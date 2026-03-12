#include <HardwareSerial.h>
#include <esp_now.h>
#include <WiFi.h>
#include <String.h>
#include <Wire.h>
#include <Adafruit_PN532.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#define WIFI_SSID   "56号"
#define WIFI_PASS   "XYZ211341"

TaskHandle_t weightReadTaskHandle = NULL;

// 用“兼容地址”最稳（不依赖 Nginx 重写）
static const char* PING_URL  = "https://xiliu.store/index.php?rest_route=/esp/v1/ping";
static const char* DEVICE_ID = "3DP-01P-petg";  // 必须与 CSV 里的 device_id 一致
static const char* TOKEN     = "TEST";          // 与插件 ESP_INGEST_TOKEN 一致

// 上报周期（毫秒）
static const uint32_t PING_INTERVAL_MS = 60000;

unsigned long lastrun = 0;

// ===== 内部状态 =====
WiFiClientSecure net;
unsigned long lastPing = 0;

// ===== 继电器发送队列 =====
static QueueHandle_t relayQueue = nullptr;

#define INVALID_WEIGHT -10000
#define REP3(x) x,x,x
#define REP4(x) x,x,x,x
// 硬件串口定义
#define RELAY_TX 4
#define RELAY_RX 15
#define WEIGH_TX 17
#define WEIGH_RX 16


// —— PN532 I2C 接口（与 PN532_1.ino 一致）——
#define PN532_SDA 21
#define PN532_SCL 22
Adafruit_PN532 nfc(PN532_SDA, PN532_SCL);

// ===== 碎冰接近开关 + 螺旋杆霍尔编码器 =====
// 碎冰：接近开关，NPN 常闭，检测到金属时输出拉高（高电平有效）
// 螺旋杆：霍尔编码器，输出脉冲（上升沿有效）
// 接线建议：棕=VCC(3.3V/5V 视模块)，蓝=GND，黑=信号 -> MCU 输入（建议外部上拉）
const int ENC1_A_PIN = 32;   // 碎冰电机接近开关信号（高电平有效）
const int ENC2_A_PIN = 33;   // 螺旋杆霍尔编码器信号（上升沿有效）

// ===== 搅动电机接近式开关（GPIO35，输入专用口，无内部上拉） =====
// 传感器特性：NPN 常闭，检测到金属时输出拉高（高电平有效）
const int STIR_ENC_PIN = 35; // 搅动电机接近式开关信号

// ===== 清洁主泵流量计（GPIO27，中断脉冲输入，上升沿有效） =====
const int CLEAN_FLOW_PIN = 27; // 清洁主泵流量计信号
static constexpr uint32_t CLEAN_FLOW_LOST_MS = 2000; // 连续无脉冲判定无流

// 检测时间窗口（毫秒）
const unsigned long CHECK_INTERVAL_MS = 100;

bool lock_judge=0;

// 中断计数：只看这段时间内有没有脉冲
volatile long encoderCount1 = 0;
volatile long encoderCount2 = 0;

static unsigned long lastrun_stir = 0;   // 空闲搅冰反转计时（每分钟一次）

// PATCH: 搅动电机脉冲计数
volatile long stirEncoderCount = 0;
// PATCH: 搅动电机软防抖（最小有效脉冲间隔）
static constexpr uint32_t STIR_MIN_PULSE_INTERVAL_US = 20000; // 20ms，显著小于约333ms的正常脉冲间隔
volatile uint32_t stirLastPulseUs = 0;
// ===== PATCH: 为RPM/卡死检测保留的累计脉冲计数（不清零） =====
volatile long encoderTotal1 = 0;
volatile long encoderTotal2 = 0;
volatile long stirEncoderTotal = 0;

// ===== 清洁主泵流量计状态 =====
volatile uint32_t cleanFlowPulseCount = 0;
volatile uint32_t cleanFlowLastPulseMs = 0;
static bool cleanFlowMonitorEnabled = false;
static bool cleanFlowPopupSent = false;

// ===== 接近开关软防抖（避免毛刺） =====
static constexpr uint32_t CRUSH_MIN_PULSE_INTERVAL_US = 20000; // 20ms
static constexpr uint32_t AUGER_MIN_PULSE_INTERVAL_US = 20000; // 20ms
volatile uint32_t crushLastPulseUs = 0;
volatile uint32_t augerLastPulseUs = 0;


enum SugarDir : uint8_t { SUGAR_OFF=0, SUGAR_FWD=1, SUGAR_REV=2 };

// —— 全局数据——
uint8_t uid[7];
uint8_t uidLen = 0;
uint8_t lastUid[7];
uint8_t lastUidLen = 0;
bool     hasCard = false;             // 当前是否检测到卡
bool     hasReadCurrentCard = false;  // 当前这张卡是否已读过一次

uint8_t keyA[6] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};  // 默认 Key A
int num1=0;

HardwareSerial SerialRelay(1);  // UART1 - 控制继电器
HardwareSerial SerialWeight(2); // UART2 - 读取称重模块

// ===== 继电器发送队列 =====
struct RelayCmd {
  uint8_t frame[8];
  uint8_t len;
  uint16_t gap_ms;
};

static void relaySendTask(void* pv) {
  RelayCmd cmd{};
  for (;;) {
    if (relayQueue && xQueueReceive(relayQueue, &cmd, portMAX_DELAY) == pdTRUE) {
      SerialRelay.write(cmd.frame, cmd.len);
      if (cmd.gap_ms > 0) {
        vTaskDelay(pdMS_TO_TICKS(cmd.gap_ms));
      }
    }
  }
}

static inline void relayWrite(const uint8_t* frame, size_t len, uint16_t gap_ms = 50) {
  if (!relayQueue) {
    SerialRelay.write(frame, len);
    if (gap_ms > 0) delay(gap_ms);
    return;
  }
  RelayCmd cmd{};
  cmd.len = (uint8_t)len;
  cmd.gap_ms = gap_ms;
  memcpy(cmd.frame, frame, len);
  xQueueSend(relayQueue, &cmd, portMAX_DELAY);
}

int reverses_num=0;

typedef struct {
    uint8_t slave_id;       // 设备地址 (1字节)
    uint8_t function_code;  // 功能码 (1字节)
    uint8_t byte_count;     // 数据字节数 (1字节)
    uint16_t register1;     // 第一个寄存器的值 (2字节)
    uint16_t register2;     // 第二个寄存器的值 (2字节)
    uint16_t crc;           // CRC校验值 (2字节)
} ModbusParsedData;

// ===== PATCH: 函数前置声明（Arduino 自动生成原型在大文件中容易失效） =====
// 编码/CRC
uint16_t calculate_crc(uint8_t *data, size_t length);
ModbusParsedData parse_modbus_message(uint8_t *buffer, size_t length);

// 继电器/电机控制（基础）
void stopMotor(int motorIndex);
void finalizeStopMotorCommon(int motorIndex);

// 糖路控制
static inline void sugarSetState(bool isU, bool use24V, uint8_t dir);

// 果酱反转清线
static void purgeJamsSequential();

// ESP-NOW 辅助打印
void printMacAddress(const uint8_t* mac);

// 串口命令入口
void processMasterCommand(const char* command);
void processSlaveCommand(const char* cmd);
void checkLoops();

// 主运行循环的电机调度
// void checkLoops();

uint8_t slaveMac1[6] = { 0xA8, 0x42, 0xE3, 0x5A, 0x6B, 0xF4 };  //是小料机
// uint8_t slaveMac2[6] = { 0xCC, 0xDB, 0xA7, 0x91, 0xD5, 0xD0 };  //泡茶机
uint8_t slaveMac2[6] = { 0x88, 0x13, 0xBF, 0x6A, 0xC3, 0x14 };  //泡茶机
typedef struct struct_message {
  char command[16];  // 命令，例如 "   "
} struct_message;
struct_message myData;

struct_message dataS1;           // 专用于小料机（slaveMac1）
char pendingSlaveCmd[16] = {0};  // 待发从机命令
bool hasPendingSlave = false;    // 是否有待发

bool ice_judge=0;  //碎冰标志位
bool hasIceAThisCycle = false;  // 本轮命令是否包含 A(搅冰)
bool hasIceBThisCycle = false;  // 本轮命令是否包含 B(碎冰)
bool ice_allow_A = false;       // 放行A（由checkTotalWeight设置）
bool ice_allow_B = false;       // 放行B（由checkTotalWeight设置）
bool speed_judge=0;//减速标志位

// 碎冰结束后等待拿杯检测，再触发小料
bool deferSlaveUntilLift = false;        // 组合命令的从机指令是否改为“拿杯后再发”
char deferredSlaveCmd[16] = {0};         // 延迟发送给小料机的指令
bool waitForCupLift = false;             // 是否正在等待拿杯
int32_t postIceWeightBaseline = 0;       // 冰机停止瞬间的总重基线
unsigned long liftDropStart = 0;         // 去抖计时
const int LIFT_DROP_THRESHOLD = 50;      // 判定“拿杯”阈值（克）
const unsigned long LIFT_DEBOUNCE_MS = 200; // 去抖时间（毫秒）


// 开关继电器指令（每个继电器根据地址进行控制）
const byte relayallOffCmd[8]={0x01, 0x06, 0x00, 0x34, 0x00, 0x00, 0xC8, 0x04 };
// 设备索引总数：原22（冰/酱/液体12/糖/水/总重）→ 新增2路液体 + 新增4路称重模块（其中用到2路） => 24
constexpr uint8_t DEVICE_COUNT = 24;

constexpr uint8_t deviceCount = DEVICE_COUNT;
const byte relayOnCmd[DEVICE_COUNT][8] = {
    {0,0,0,0,0,0,0,0 },   //设备地址 30
    // { 0x1F, 0x05, 0x00, 0x00, 0xFF, 0x00, 0x8F, 0x84 },   //设备地址 31
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},  
    {0,0,0,0,0,0,0,0},  
    {0,0,0,0,0,0,0,0},  
    {0,0,0,0,0,0,0,0},
    { 0x01, 0x06, 0x00, 0x00, 0x00, 0x01, 0x48, 0x0A },  // 液体1
    { 0x01, 0x06, 0x00, 0x01, 0x00, 0x01, 0x19, 0xCA },  // 液体2
    { 0x01, 0x06, 0x00, 0x02, 0x00, 0x01, 0xE9, 0xCA },  // 液体3
    { 0x01, 0x06, 0x00, 0x03, 0x00, 0x01, 0xB8, 0x0A },  // 液体4
    { 0x01, 0x06, 0x00, 0x04, 0x00, 0x01, 0x09, 0xCB },  // 液体5
    { 0x01, 0x06, 0x00, 0x05, 0x00, 0x01, 0x58, 0x0B },  // 液体6
    { 0x01, 0x06, 0x00, 0x06, 0x00, 0x01, 0xA8, 0x0B },  // 液体7
    { 0x01, 0x06, 0x00, 0x07, 0x00, 0x01, 0xF9, 0xCB },  // 液体8
    { 0x01, 0x06, 0x00, 0x08, 0x00, 0x01, 0xC9, 0xC8 },  // 液体9
    { 0x01, 0x06, 0x00, 0x09, 0x00, 0x01, 0x98, 0x08 },  // 液体10
    { 0x01, 0x06, 0x00, 0x0A, 0x00, 0x01, 0x68, 0x08 },  // 液体11
    { 0x01, 0x06, 0x00, 0x0B, 0x00, 0x01, 0x39, 0xC8 },  // 液体12
    { 0x01, 0x06, 0x00, 0x0C, 0x00, 0x01, 0x88, 0x09 },  // 液体13（新增，地址0x01继电器第13路）
    { 0x01, 0x06, 0x00, 0x0D, 0x00, 0x01, 0xD9, 0xC9 },  // 液体14（新增，地址0x01继电器第14路）
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
};
const byte relayOffCmd[DEVICE_COUNT][8] = {
    {0,0,0,0,0,0,0,0 },  //设备地址 30
    {0,0,0,0,0,0,0,0},  // 液体5
    {0,0,0,0,0,0,0,0},  // 设备地址 9
    {0,0,0,0,0,0,0,0},  // 设备地址 10
    {0,0,0,0,0,0,0,0},  // 设备地址 11
    {0,0,0,0,0,0,0,0},
    { 0x01, 0x06, 0x00, 0x00, 0x00, 0x00, 0x89, 0xCA },  // 液体1
    { 0x01, 0x06, 0x00, 0x01, 0x00, 0x00, 0xD8, 0x0A },  // 液体2
    { 0x01, 0x06, 0x00, 0x02, 0x00, 0x00, 0x28, 0x0A },  // 液体3
    { 0x01, 0x06, 0x00, 0x03, 0x00, 0x00, 0x79, 0xCA },  // 液体4
    { 0x01, 0x06, 0x00, 0x04, 0x00, 0x00, 0xC8, 0x0B },  // 液体5
    { 0x01, 0x06, 0x00, 0x05, 0x00, 0x00, 0x99, 0xCB },  // 液体6
    { 0x01, 0x06, 0x00, 0x06, 0x00, 0x00, 0x69, 0xCB },  // 液体7
    { 0x01, 0x06, 0x00, 0x07, 0x00, 0x00, 0x38, 0x0B },  // 液体8
    { 0x01, 0x06, 0x00, 0x08, 0x00, 0x00, 0x08, 0x08 },  // 液体9
    { 0x01, 0x06, 0x00, 0x09, 0x00, 0x00, 0x59, 0xC8 },  // 液体10
    { 0x01, 0x06, 0x00, 0x0A, 0x00, 0x00, 0xA9, 0xC8 },  // 液体11
    { 0x01, 0x06, 0x00, 0x0B, 0x00, 0x00, 0xF8, 0x08 },  // 液体12
    { 0x01, 0x06, 0x00, 0x0C, 0x00, 0x00, 0x49, 0xC9 },  // 液体13 OFF（新增）
    { 0x01, 0x06, 0x00, 0x0D, 0x00, 0x00, 0x18, 0x09 },  // 液体14 OFF（新增）
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0},
};
// const byte relayOnCmd_2[8][8] = {
//     { 0x03, 0x06, 0x00, 0x00, 0x00, 0x01, 0x49, 0xE8 },  // 果酱1
//     { 0x03, 0x06, 0x00, 0x01, 0x00, 0x01, 0x18, 0x28 },  
//     { 0x03, 0x06, 0x00, 0x02, 0x00, 0x01, 0xE8, 0x28 },  // 果酱2
//     { 0x03, 0x06, 0x00, 0x03, 0x00, 0x01, 0xB9, 0xE8 },  
//     { 0x03, 0x06, 0x00, 0x04, 0x00, 0x01, 0x08, 0x29 },  // 果酱3
//     { 0x03, 0x06, 0x00, 0x05, 0x00, 0x01, 0x59, 0xE9 },  
//     { 0x03, 0x06, 0x00, 0x06, 0x00, 0x01, 0xA9, 0xE9 },  // 果酱4
//     { 0x03, 0x06, 0x00, 0x07, 0x00, 0x01, 0xF8, 0x29 },  
// };
// const byte relayOffCmd_2[8][8] = {
//     { 0x03, 0x06, 0x00, 0x00, 0x00, 0x00, 0x88, 0x28 },  // 果酱1
//     { 0x03, 0x06, 0x00, 0x01, 0x00, 0x00, 0xD9, 0xE8 },  
//     { 0x03, 0x06, 0x00, 0x02, 0x00, 0x00, 0x29, 0xE8 },  // 果酱2
//     { 0x03, 0x06, 0x00, 0x03, 0x00, 0x00, 0x78, 0x28 },  
//     { 0x03, 0x06, 0x00, 0x04, 0x00, 0x00, 0xC9, 0xE9 },  // 果酱3
//     { 0x03, 0x06, 0x00, 0x05, 0x00, 0x00, 0x98, 0x29 },  
//     { 0x03, 0x06, 0x00, 0x06, 0x00, 0x00, 0x68, 0x29 },  // 果酱4
//     { 0x03, 0x06, 0x00, 0x07, 0x00, 0x00, 0x39, 0xE9 },  
// };
const byte relayOnCmd_3[5][8]={//冰逻辑
       //增加螺旋杆地址0x1e
    { 0x02, 0x06, 0x00, 0x00, 0x00, 0x01, 0x48, 0x39 },//螺旋杆正转
    { 0x02, 0x06, 0x00, 0x01, 0x00, 0x01, 0x19, 0xF9 },//螺旋杆反转
    { 0x02, 0x06, 0x00, 0x02, 0x00, 0x01, 0xE9, 0xF9 },//12V和24V切换
    { 0x02, 0x06, 0x00, 0x03, 0x00, 0x01, 0xB8, 0x39 },//冰机正转
    { 0x02, 0x06, 0x00, 0x04, 0x01, 0x2C, 0xC8, 0x75 }//冰机反转
};

const byte relayOffCmd_3[5][8]={
      //增加螺旋杆地址0x1e
    { 0x02, 0x06, 0x00, 0x00, 0x00, 0x00, 0x89, 0xF9 }, 
    { 0x02, 0x06, 0x00, 0x01, 0x00, 0x00, 0xD8, 0x39 },
    { 0x02, 0x06, 0x00, 0x02, 0x00, 0x00, 0x28, 0x39 },
    { 0x02, 0x06, 0x00, 0x03, 0x00, 0x00, 0x79, 0xF9 },
    { 0x02, 0x06, 0x00, 0x04, 0x00, 0x01, 0x09, 0xF8 }
};

// ===== PATCH: 地址2(0x02) 继电器第7/8位用于“搅动电机”正/反 =====
// 规则：第7位与第8位都关闭 -> 停止；第7开第8关 -> 正转；第7关第8开 -> 反转
// 注：这里按常见 8路编号(1..8) 映射到寄存器 0..7，因此第7/8位 = 寄存器 0x0006/0x0007。
const byte relayOnCmd_ICE_STIR_FWD[8]  = { 0x02, 0x06, 0x00, 0x06, 0x00, 0x01, 0xA8, 0x38 }; // reg6 ON
const byte relayOffCmd_ICE_STIR_FWD[8] = { 0x02, 0x06, 0x00, 0x06, 0x00, 0x00, 0x69, 0xF8 }; // reg6 OFF
const byte relayOnCmd_ICE_STIR_REV[8]  = { 0x02, 0x06, 0x00, 0x07, 0x00, 0x01, 0xF9, 0xF8 }; // reg7 ON
const byte relayOffCmd_ICE_STIR_REV[8] = { 0x02, 0x06, 0x00, 0x07, 0x00, 0x00, 0x38, 0x38 }; // reg7 OFF


// ===== PATCH: 电机方向标记（用于“卡住反转脱困”） =====
enum MotorDir : int8_t { DIR_STOP = 0, DIR_FWD = 1, DIR_REV = -1 };
static volatile int8_t iceMotorDir  = DIR_STOP; // 碎冰电机（冰机）方向（relayOnCmd_3[3]/[4]）
static volatile int8_t augerMotorDir= DIR_STOP; // 螺旋杆方向（relayOnCmd_3[0]/[1]）
static volatile int8_t stirMotorDir = DIR_STOP; // 搅冰电机方向（地址2第7/8位）

// ===== PATCH: 搅动电机控制（地址2第7/8位） =====
inline void stirMotorStop() {
  relayWrite(relayOffCmd_ICE_STIR_FWD, 8);
  delay(50);
  relayWrite(relayOffCmd_ICE_STIR_REV, 8);
  delay(50);
  stirMotorDir = DIR_STOP;
}

inline void stirMotorForward() {
  // 先确保反转位关闭，再打开正转位
  relayWrite(relayOffCmd_ICE_STIR_REV, 8);
  delay(30);
  relayWrite(relayOnCmd_ICE_STIR_FWD, 8);
  delay(30);
  stirMotorDir = DIR_FWD;
}

inline void stirMotorReverse() {
  // 先确保正转位关闭，再打开反转位
  relayWrite(relayOffCmd_ICE_STIR_FWD, 8);
  delay(30);
  relayWrite(relayOnCmd_ICE_STIR_REV, 8);
  delay(30);
  stirMotorDir = DIR_REV;
}

// ===== PATCH: 碎冰电机（冰机）方向控制封装（保持你原有寄存器/CRC不变） =====
inline void iceMotorStop() {
  relayWrite(relayOffCmd_3[3], 8);
  delay(50);
  relayWrite(relayOffCmd_3[4], 8);
  delay(50);
  iceMotorDir = DIR_STOP;
}

inline void iceMotorForward() {
  relayWrite(relayOffCmd_3[4], 8);
  delay(50);
  relayWrite(relayOnCmd_3[3], 8);
  delay(50);
  iceMotorDir = DIR_FWD;
}

inline void iceMotorReverse() {
  relayWrite(relayOffCmd_3[3], 8);
  delay(50);
  relayWrite(relayOnCmd_3[4], 8);
  delay(50);
  iceMotorDir = DIR_REV;
}

// ===== PATCH: 传送带/搅冰(螺旋杆) 电机（0/1）方向控制封装 =====
// 规则：0/1 都关闭=停止；0开1关=正转；0关1开=反转
inline void augerMotorStop() {
  relayWrite(relayOffCmd_3[0], 8);
  delay(30);
  relayWrite(relayOffCmd_3[1], 8);
  delay(30);
  augerMotorDir = DIR_STOP;
}

inline void augerMotorForward() {
  relayWrite(relayOffCmd_3[1], 8);
  delay(30);
  relayWrite(relayOnCmd_3[0], 8);
  delay(30);
  augerMotorDir = DIR_FWD;
}

inline void augerMotorReverse() {
  relayWrite(relayOffCmd_3[0], 8);
  delay(30);
  relayWrite(relayOnCmd_3[1], 8);
  delay(30);
  augerMotorDir = DIR_REV;
}



// ============================================================================
// ===== PATCH: 碎冰/搅冰(传送带)/搅动 电机 —— 三个独立状态机（卡死检测+反转解卡+RPM打印） =====
// 说明：
// - 碎冰电机：继电器 3/4（iceMotorForward/Reverse/Stop），编码器=ENC1_A_PIN
// - 搅冰(传送带/螺旋杆)：继电器 0/1（augerMotorForward/Reverse/Stop），编码器=ENC2_A_PIN
// - 搅动电机：继电器 7/8（stirMotorForward/Reverse/Stop），霍尔编码器=GPIO35
// 你只需调整下面三个 PULSES_PER_REV_* 常量为真实硬件的“每转脉冲数”。
// ============================================================================

static constexpr float PULSES_PER_REV_CRUSH = 20.0f; // 碎冰电机编码器：每转脉冲数（按实际改）
static constexpr float PULSES_PER_REV_AUGER = 20.0f; // 传送带/搅冰编码器：每转脉冲数（按实际改）
static constexpr float PULSES_PER_REV_STIR  = 6.0f;  // 光电：每转6脉冲（6个监测点）

struct MotorFSM {
  enum State : uint8_t {
    IDLE = 0,
    RUN_FWD,
    RUN_REV,
    ESCAPE,     // 临时换向脱困
    SETTLE,     // 停机缓冲
    FAULT
  };

  // --- 绑定 ---
  const char*     tag = "M";
  volatile long*  totalCounter = nullptr;  // ISR 累计脉冲
  void (*doStop)() = nullptr;
  void (*doFwd)()  = nullptr;
  void (*doRev)()  = nullptr;

  // --- 配置 ---
  float    pulsesPerRev = 1.0f;
  uint16_t stallWinMs   = 150;
  uint8_t  stallNeedWin = 5;
  int32_t  minPulsesPerWin = 1;
  uint16_t escapeMs     = 700;
  bool     enableStall  = true;
  uint16_t settleMs     = 80;
  uint8_t  maxEscape    = 6;
  // uint16_t rpmPrintMs   = 500;

  // --- 状态 ---
  State   st       = IDLE;
  int8_t  wantDir  = DIR_STOP;   // 期望方向（只支持 STOP/FWD；解卡时会临时换向）
  int8_t  runDir   = DIR_STOP;   // 当前执行方向
  int8_t  escapeDir = DIR_STOP;  // ESCAPE 临时方向
  uint32_t stAt    = 0;
  uint8_t  stallWinCnt = 0;
  uint8_t  escapeCnt   = 0;

  // --- 采样 ---
  long     lastStallTotal = 0;
  uint32_t lastStallMs    = 0;
  // long     lastRpmTotal   = 0;
  // uint32_t lastRpmMs      = 0;

  void bind(const char* _tag, volatile long* _total, float _ppr,
            void (*_stop)(), void (*_fwd)(), void (*_rev)()) {
    tag = _tag;
    totalCounter = _total;
    pulsesPerRev = (_ppr <= 0.0f) ? 1.0f : _ppr;
    doStop = _stop;
    doFwd  = _fwd;
    doRev  = _rev;
    reset();
  }

  void reset() {
    st = IDLE;
    wantDir = DIR_STOP;
    runDir  = DIR_STOP;
    escapeDir = DIR_STOP;
    stAt = millis();
    stallWinCnt = 0;
    escapeCnt = 0;
    lastStallMs = millis();
  //   lastRpmMs   = millis();
  }

  // 外部只设置“想要持续运行的方向”（通常是 DIR_FWD 或 DIR_STOP）
  inline void requestDir(int8_t dir) {
    wantDir = dir;
  }

  // 立即停机并回到 IDLE（用于 stopMotor / 超时）
  void forceStop() {
    if (doStop) doStop();
    st = IDLE;
    runDir = DIR_STOP;
    wantDir = DIR_STOP;
    stallWinCnt = 0;
    escapeCnt = 0;
  }

  void _enterRun(int8_t dir, uint32_t nowMs) {
    if (dir == DIR_FWD) {
      if (doFwd) doFwd();
      runDir = DIR_FWD;
      st = RUN_FWD;
    } else if (dir == DIR_REV) {
      if (doRev) doRev();
      runDir = DIR_REV;
      st = RUN_REV;
    } else {
      if (doStop) doStop();
      runDir = DIR_STOP;
      st = IDLE;
    }
    stAt = nowMs;
  }

  void _startEscape(uint32_t nowMs) {
    // 超过次数：进入 FAULT
    if (++escapeCnt > maxEscape) {
      if (doStop) doStop();
      st = FAULT;
      runDir = DIR_STOP;
      Serial.printf("[%s] FAULT: too many escapes\n", tag);
      return;
    }

    // 换向脱困：FWD->REV / REV->FWD
    escapeDir = (runDir == DIR_FWD) ? DIR_REV : DIR_FWD;

    if (doStop) doStop();
    delay(20);
    if (escapeDir == DIR_REV) { if (doRev) doRev(); }
    else { if (doFwd) doFwd(); }

    st = ESCAPE;
    stAt = nowMs;
    Serial.printf("[%s] stall -> escape(%s)\n", tag, (escapeDir==DIR_REV?"REV":"FWD"));
  }

  void _enterSettle(uint32_t nowMs) {
    if (doStop) doStop();
    runDir = DIR_STOP;
    st = SETTLE;
    stAt = nowMs;
  }

  // 返回窗口内增量脉冲
  inline long _deltaTotal(long &lastTotal) {
    long cur;
    noInterrupts();
    cur = totalCounter ? *totalCounter : 0;
    interrupts();
    long d = cur - lastTotal;
    lastTotal = cur;
    return d;
  }

  void tick(uint32_t nowMs) {
    if (!totalCounter || !doStop || !doFwd || !doRev) return;

    // --- RPM 打印（不依赖方向；只要在转或处于RUN/ESCAPE就打印） ---
    // if (nowMs - lastRpmMs >= rpmPrintMs) {
    //   uint32_t dt = nowMs - lastRpmMs;
    //   long dp = _deltaTotal(lastRpmTotal);
    //   float rpm = 0.0f;
    //   if (dt > 0) rpm = (dp / pulsesPerRev) * (60000.0f / (float)dt);
    //   if (st != IDLE || dp > 0) {
    //     Serial.printf("[%s] rpm=%.1f pulses=%ld state=%u\n", tag, rpm, dp, (unsigned)st);
    //   }
    //   lastRpmMs = nowMs;
    // }

    // --- FAULT：保持停机，等待外部 stopMotor/复位（你也可在此加自动恢复策略） ---
    if (st == FAULT) {
      return;
    }

    // --- 期望=STOP：立即停机 ---
    if (wantDir == DIR_STOP) {
      if (st != IDLE) {
        _enterSettle(nowMs);
      }
    }

    // --- SETTLE：停机缓冲结束后，若仍期望运行则进入运行 ---
    if (st == SETTLE) {
      if (nowMs - stAt >= settleMs) {
        if (wantDir == DIR_FWD) _enterRun(DIR_FWD, nowMs);
        else if (wantDir == DIR_REV) _enterRun(DIR_REV, nowMs);
        else { st = IDLE; runDir = DIR_STOP; }
      }
      return;
    }

    // --- IDLE：若期望运行则进入运行 ---
    if (st == IDLE) {
      if (wantDir == DIR_FWD) _enterRun(DIR_FWD, nowMs);
      else if (wantDir == DIR_REV) _enterRun(DIR_REV, nowMs);
      return;
    }

    // --- ESCAPE：到时后停机缓冲，然后回到期望方向 ---
    if (st == ESCAPE) {
      if (nowMs - stAt >= escapeMs) {
        _enterSettle(nowMs);
      }
      return;
    }

    // --- RUN 状态：卡死检测（连续多个窗口无脉冲） ---
    if ((st == RUN_FWD) || (st == RUN_REV)) {
      if (enableStall && totalCounter && pulsesPerRev > 0.0f && (nowMs - lastStallMs >= stallWinMs)) {
        long dp = _deltaTotal(lastStallTotal);
        const bool moving = (dp >= minPulsesPerWin);
        if (moving) {
          stallWinCnt = 0;
          escapeCnt = 0; // 一旦检测到在动，清空脱困计数
        } else {
          if (++stallWinCnt >= stallNeedWin) {
            stallWinCnt = 0;
            _startEscape(nowMs);
            return;
          }
        }
        lastStallMs = nowMs;
      }
    }
  }
};

// 三个独立模块实例
static MotorFSM fsmCrush; // 碎冰电机(3/4)
static MotorFSM fsmAuger; // 传送带/搅冰(0/1)
static MotorFSM fsmStir;  // 搅动电机(7/8)

// 空闲反转调度（对齐旧版方向规则）：空闲且有冰时，A(搅冰电机7/8) 与 B(碎冰电机3/4) 定时反转
// - 工作阶段：A/B 正转（由 loop() 里的 workA/workB 决定）
// - 空闲阶段：每 60s 反转 3s（仅当 allMotorsInactive && hasIce）
static inline void iceIdleReverseScheduler(uint32_t nowMs, bool enableIdle, bool hasIce) {
  static uint32_t lastTrig = 0;
  static bool     running  = false;
  static uint32_t startAt  = 0;

  const uint32_t PERIOD_MS = 60000; // 每 60s
  const uint32_t RUN_MS    = 3000;  // 反转 3s

  // 非空闲或没冰：退出调度，不抢控制，并重置计时
  if (!enableIdle || !hasIce) {
    running  = false;
    lastTrig = nowMs;  // 重置空闲计时，避免刚结束就立即反转
    return;
  }

  if (!running) {
    if (nowMs - lastTrig >= PERIOD_MS) {
      lastTrig = nowMs;
      running  = true;
      startAt  = nowMs;

      // 仅搅冰电机 A：空闲反转
      fsmStir.requestDir(DIR_REV);
      Serial.printf("[IDLE_FSM] start rev: now=%lu enableIdle=%d hasIce=%d\n",
                    (unsigned long)nowMs, enableIdle ? 1 : 0, hasIce ? 1 : 0);
    }
  } else {
    if (nowMs - startAt >= RUN_MS) {
      // 结束：停搅冰
      fsmStir.requestDir(DIR_STOP);
      running = false;
      Serial.printf("[IDLE_FSM] stop: now=%lu\n", (unsigned long)nowMs);
    }
  }
}

//控制糖路的开关
const byte relayOnCmd_2[8][8] = {
  { 0x03, 0x06, 0x00, 0x00, 0x00, 0x01, 0x49, 0xE8 },  // 寄存器0 -> 继电器1 ON
  { 0x03, 0x06, 0x00, 0x01, 0x00, 0x01, 0x18, 0x28 },  // 寄存器1 -> 继电器2 ON
  { 0x03, 0x06, 0x00, 0x02, 0x00, 0x01, 0xE8, 0x28 },  // 继电器3 ON
  { 0x03, 0x06, 0x00, 0x03, 0x00, 0x01, 0xB9, 0xE8 },  // 继电器4 ON
  { 0x03, 0x06, 0x00, 0x04, 0x00, 0x01, 0x08, 0x29 },  // 继电器5 ON
  { 0x03, 0x06, 0x00, 0x05, 0x00, 0x01, 0x59, 0xE9 },  // 继电器6 ON
};
const byte relayOffCmd_2[8][8] = {
  { 0x03, 0x06, 0x00, 0x00, 0x00, 0x00, 0x88, 0x28 },  // 继电器1 OFF
  { 0x03, 0x06, 0x00, 0x01, 0x00, 0x00, 0xD9, 0xE8 },  // 继电器2 OFF
  { 0x03, 0x06, 0x00, 0x02, 0x00, 0x00, 0x29, 0xE8 },  // 继电器3 OFF
  { 0x03, 0x06, 0x00, 0x03, 0x00, 0x00, 0x78, 0x28 },  // 继电器4 OFF
  { 0x03, 0x06, 0x00, 0x04, 0x00, 0x00, 0xC9, 0xE9 },  // 继电器5 OFF
  { 0x03, 0x06, 0x00, 0x05, 0x00, 0x00, 0x98, 0x29 },  // 继电器6 OFF
};

// 果酱继电器（地址0x03）从第11位开始：两路控制一个通道（每通道占用相邻2路）
// 对应寄存器 0x000A..0x0011（继电器第11~18位）
const byte relayOnCmd_4[8][8] = {
  { 0x03, 0x06, 0x00, 0x0A, 0x00, 0x01, 0x69, 0xEA },  // 位11 ON
  { 0x03, 0x06, 0x00, 0x0B, 0x00, 0x01, 0x38, 0x2A },  // 位12 ON
  { 0x03, 0x06, 0x00, 0x0C, 0x00, 0x01, 0x89, 0xEB },  // 位13 ON
  { 0x03, 0x06, 0x00, 0x0D, 0x00, 0x01, 0xD8, 0x2B },  // 位14 ON
  { 0x03, 0x06, 0x00, 0x0E, 0x00, 0x01, 0x28, 0x2B },  // 位15 ON
  { 0x03, 0x06, 0x00, 0x0F, 0x00, 0x01, 0x79, 0xEB },  // 位16 ON
  { 0x03, 0x06, 0x00, 0x10, 0x00, 0x01, 0x48, 0x2D },  // 位17 ON
  { 0x03, 0x06, 0x00, 0x11, 0x00, 0x01, 0x19, 0xED },  // 位18 ON
};
const byte relayOffCmd_4[8][8] = {
  { 0x03, 0x06, 0x00, 0x0A, 0x00, 0x00, 0xA8, 0x2A },  // 位11 OFF
  { 0x03, 0x06, 0x00, 0x0B, 0x00, 0x00, 0xF9, 0xEA },  // 位12 OFF
  { 0x03, 0x06, 0x00, 0x0C, 0x00, 0x00, 0x48, 0x2B },  // 位13 OFF
  { 0x03, 0x06, 0x00, 0x0D, 0x00, 0x00, 0x19, 0xEB },  // 位14 OFF
  { 0x03, 0x06, 0x00, 0x0E, 0x00, 0x00, 0xE9, 0xEB },  // 位15 OFF
  { 0x03, 0x06, 0x00, 0x0F, 0x00, 0x00, 0xB8, 0x2B },  // 位16 OFF
  { 0x03, 0x06, 0x00, 0x10, 0x00, 0x00, 0x89, 0xED },  // 位17 OFF
  { 0x03, 0x06, 0x00, 0x11, 0x00, 0x00, 0xD8, 0x2D },  // 位18 OFF
};


const byte CleanOnCmd[2][8]={
  {0x03, 0x06, 0x00, 0x06, 0x00, 0x01, 0xA9, 0xEA },
  {0x03, 0x06, 0x00, 0x07, 0x00, 0x01, 0xF8, 0x2A },
};
const byte CleanOffCmd[2][8]={
  {0x03, 0x06, 0x00, 0x06, 0x00, 0x00, 0x68, 0x2A },
  {0x03, 0x06, 0x00, 0x07, 0x00, 0x00, 0x39, 0xEA },
};

float flow_rata[3]={6.2,4.2,32};

constexpr uint8_t IDX_ICE     = 0;   // 冰重（0x01）
constexpr uint8_t IDX_CRUSHED = 1;   // 碎冰（0x01）
constexpr uint8_t IDX_WATER   = 22;  // 水（原20，因新增2路液体后顺延）
constexpr uint8_t IDX_TOTAL   = 23;  // 总重（原21，因新增2路液体后顺延）

constexpr uint8_t JAM_START = 2,  JAM_END = 5;   // CDEF: 果酱4路
constexpr uint8_t LIQ_START = 6,  LIQ_END = 19;  // 液体：12→14 路  // F..K: 液体
constexpr uint8_t SUG_START = 20, SUG_END = 21;  // 糖：顺延    // 糖  L..M

static inline bool isIceIdx(uint8_t i)     { return (i == IDX_ICE || i == IDX_CRUSHED); }
static inline bool isTotalIdx(uint8_t i)   { return (i == IDX_TOTAL); }
static inline bool isJamIdx(uint8_t i)     { return (i >= JAM_START && i <= JAM_END); }
static inline bool isLiquidIdx(uint8_t i)  { return (i >= LIQ_START && i <= LIQ_END); }
static inline bool isSugarIdx(uint8_t i){ return (i >= SUG_START && i <= SUG_END); }
static inline bool isWaterIdx(uint8_t i)   { return (i == IDX_WATER); }

static bool hasPumpThisCycle = false;
static bool hasIceThisCycle  = false;
static bool jamRanThisCycle[deviceCount] = {false};
static bool purgeInProgress = false;
static bool purgeDoneThisCycle = false;

static bool         sugarActive[deviceCount]   = {false};
static unsigned long sugarStartMs[deviceCount] = {0};
static uint32_t     sugarStopMs [deviceCount]  = {0};   // 目标时长（毫秒）

//AB CDE FGH IJK LMN OPQ RST UVW XYZ
//0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x0C,0x0D,0x0E,0x0f,0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x09,0x0A,0x0B,0x1F,0x1F

// 新增：4路称重变送模块（用于液体13/14），请将硬件Modbus地址设置为该值
constexpr uint8_t LIQUID_4CH_ADDR = 0x04; // 新增4路称重模块地址（可按实际改）
constexpr uint8_t LIQ_4CH_START = 18, LIQ_4CH_END = 19; // 液体13/14 对应的索引区间
const uint8_t liq4ch_offsets[2] = {0x04, 0x06}; // 4路模块中第1/2路寄存器起始偏移
const uint8_t deviceAddresses[DEVICE_COUNT] = {0x01,0x01,REP4(0x05),REP4(0x02),REP4(0x02),REP4(0x02),LIQUID_4CH_ADDR,LIQUID_4CH_ADDR,0x03,0x03,0x03,0x01}; // 变送模块设备地址（新增两路液体称重）
// PATCH: deviceCount moved to top (constexpr)// const uint8_t addresses[3] = {0x06,0x04,0x02};
// 果酱（C/D/E）使用地址0x05的第2/3/4路寄存器偏移
const uint8_t jam_offsets[4] = {0x02, 0x04, 0x06, 0x08};
//十二路的寄存器地址，用于区分12路液体
const uint8_t addresses[12] = {
  0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10,0x12,0x14,0x16
};
const int AREA_TARGET_RATIO_1 = 21;    // 条件2的面积比例
const int AREA_TARGET_RATIO_2 = 18.5;  // 条件4的面积比例
const int WEIGHT_WINDOW_1 = 24;        // 1的窗口大小
const int WEIGHT_WINDOW_2 = 15;         
const int WEIGHT_WINDOW_3 = 12;

struct IceMotorStatus {
  int pointsInWindow1 = 0;       // 条件1计数器
  int pointsInWindow2 = 0;       // 条件3计数器
  int pointsInWindow3 = 0;       
  int accumulatedArea = 0;       // 累计面积
  int lastWeightDiff = 0;        // 上次重量差
  unsigned long lastUpdateTime = 0; // 上次更新时间
};
IceMotorStatus iceStatus[deviceCount]; // 每个电机一个状态

struct IceMotorStatus_2 {
  int pointsInWindow1 = 0;       // 条件1计数器
  int pointsInWindow2 = 0;       // 条件2计数器
  int pointsInWindow3 = 0;       
};
IceMotorStatus_2 iceStatus_2; // 每个电机一个状态
IceMotorStatus_2 iceStatus_3; // 每个电机一个状态

bool allMotorsInactive = true;  //标志变量，用于指示是否所有电机都处于非激活状态。
const char sta_ch = 'A';  //用于将电机索引转换为字符，方便命令字符串的解析。
bool commandReceived = false;
bool isProcessingCommand = false;
uint8_t addr = 0;  //启动继电器地址
uint8_t addr_2 = 0;
bool motorActive[deviceCount] = { false };  //电机运行状态
int32_t Weights[deviceCount] = { 
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0,
  500, 500, 0, 0
};  //重量值（U/V 初始值=100）

int32_t lastWeights[deviceCount] = { 0 }; // 获取时的上一次的重量值
int targetWeights[deviceCount] = { 0 };  //重量目标值
int baselineWeights[deviceCount] = { 0 };  //重量基础值



int weightDiff[deviceCount] = { 0 };  //重量差值
bool baseInit_judge[deviceCount]={false};

int target_diff[deviceCount] = {
  // A..X（共 24 路）补偿值
  0,0,28,27,25,25,23,22,21,20,19,22,22,21,23,26,23,22,26,24,0,0,0,0
}; 
int liquid_diff[deviceCount] = {0,0,0,0,0,0,0,0,0,0,0}; //0,0,8,16,10,17,18,16,18
int suib = 1;  //碎冰模块地址  在传送带模块地址的后一个
int csd = 0;   //传送带地址  

//电机启动超时检测
int timer = 20000;//电机运行超时时间（兜底：当单通道 max_time_to_stop 未计算时使用）
unsigned long time_check_to_stop[deviceCount] = {0}; //时间与重量双重监测
unsigned long last_time_check_to_stop[deviceCount] = {0};
unsigned long max_time_to_stop[deviceCount] = {0}; // 每通道独立超时上限（毫秒）

// ===== 每通道“期望出料时长”估算（用于超时兜底） =====
// 可按实际标定修改：单位 g/s
static constexpr float DEFAULT_LIQUID_RATE_GPS = 6.0f; // 液体通用速率
static constexpr float DEFAULT_ICE_RATE_GPS    = 10.0f; // 冰通用速率

static inline float getChannelRateGps(uint8_t i) {
  if (isSugarIdx(i)) return flow_rata[i - SUG_START]; // U/V
  if (isWaterIdx(i)) return flow_rata[2];             // W
  if (isLiquidIdx(i)) return DEFAULT_LIQUID_RATE_GPS; // 液体
  if (i == IDX_ICE || i == IDX_CRUSHED) return DEFAULT_ICE_RATE_GPS; // 冰
  return DEFAULT_LIQUID_RATE_GPS; // 其它通道默认按液体处理
}

static inline uint32_t calcChannelMaxMs(uint8_t i, int grams) {
  const float rate = getChannelRateGps(i);
  if (rate <= 0.01f) return 0;
  float expected_ms = (fabsf((float)grams) / rate) * 1000.0f;
  if (expected_ms < 50.0f) expected_ms = 50.0f;
  if (expected_ms > 3600000.0f) expected_ms = 3600000.0f; // 1h 上限
  return (uint32_t)(expected_ms * 1.5f + 1000.0f);
}

//反转部分
bool isNegative = false;
unsigned long motorStartTime[deviceCount]={0}; // 反转电机启动的时间
int motorRunDuration[deviceCount]={0};         // 反转目标运行时间
bool relayRunning[deviceCount] = {false};  // 反转标志是否处于执行状态

int num = 0;//判断是否是 水，果酱，碎冰
bool csdStop = false; //传送带启动标志

int32_t reallweight[deviceCount]={0};   //理论出料后的重量
int32_t beforeDischargeWeights[deviceCount] = {0}; // 出料前的重量
int32_t afterDischargeWeights[deviceCount] = {0};  // 出料后的重量
int32_t actualDischargeAmounts[deviceCount] = {0}; // 实际出料量
unsigned long dischargeCompleteTime[deviceCount] = {0}; // 出料完成时间
bool isRecordingDischarge[deviceCount] = {false}; // 是否正在记录出料

//用于总重量传感器
int WEIGHT_DIFF_1 = 20;  //总重量的提前停止余量1
int WEIGHT_DIFF_2 = 10;  //总重量的提前停止余量2
int WEIGHT_DIFF_3 = 5;
int totalTargetWeight = 0;  // 命令中所有目标重量之和
int totalTargetWeight_pre = 0;
int totalTargetWeight_diff = 20;
int32_t totalBaselineWeight = 0;  // 总重量传感器的初始重量
bool totalWeightCheckEnabled = false;  // 是否启用总重量检查
unsigned long lastUpdateTime = 0;

int  liquidsTargetSum        = 0;   // “水路”（不含A/B冰）的目标量之和（含果酱）
int  liquidsStageThresholdAbs= 0;   // 第一次阈值（绝对重量）：达到后先停水路、再开冰
int  liquidsTargetSumAbs   = 0;   // 本单杯参与“第一次判定”的水路目标量之和（不含 A/B/总重）
int  liquidsCompSum        = 0;   // 这些水路对应的惯性补偿之和：∑target_diff[i]
int  liquidsThresholdAbs   = 0;   // 第一次阈值（绝对重量）：liquidsTargetSumAbs - liquidsCompSum
bool liquidsStageTriggered   = false;// 是否已触发“先停水路”阶段

unsigned long de_time = 0;


// ===== 总重量百分比联动（新增） =====
bool totalSlowdownTriggered = false;   // 85% 已减速
bool totalStopTriggered     = false;   // 95% 已全停
bool Slowdown_judge=0;   //确保传送带先减速再停止

const float TOTAL_SLOWDOWN_RATIO = 0.67f; // 85% 减速
const float TOTAL_STOP_RATIO     = 0.90f; // 95% 停止

// === RS-485 发帧节流（全局互斥/定时） ===
static uint32_t relayBusFreeAt = 0;


// ========= 软复位：用于每轮开始前，清理跨轮状态，不触碰 Weights[] / 补偿表 =========
void resetForNewCycle() {
  // —— 指令/流程状态 —— 
  commandReceived        = false;
  isProcessingCommand    = false;
  totalWeightCheckEnabled= false;

  purgeInProgress        = false;
  purgeDoneThisCycle     = false;
  hasPumpThisCycle       = false;
  hasIceThisCycle        = false;
  hasIceAThisCycle       = false;
  hasIceBThisCycle       = false;
  ice_allow_A            = false;
  ice_allow_B            = false;

  liquidsStageTriggered  = false;
  totalSlowdownTriggered = false;
  totalStopTriggered     = false;

  // —— 85%/95% 状态门 —— 
  // speed_judge            = 1;   // 注意：运行期应置 1 才能触发 85%减速
  Slowdown_judge         = 0;
  ice_judge              = 0;

  // —— 从机延后/拿杯等待 —— 
  deferSlaveUntilLift    = false;
  waitForCupLift         = false;
  hasPendingSlave        = false;
  pendingSlaveCmd[0]     = '\0';
  deferredSlaveCmd[0]    = '\0';

  // —— 继电器/计时 —— 
  for (int i=0; i<deviceCount; ++i) {
    relayRunning[i]          = false;
    motorStartTime[i]        = 0;
    motorRunDuration[i]      = 0;
    time_check_to_stop[i]    = 0;
    max_time_to_stop[i]      = 0;
    last_time_check_to_stop[i]=0;
    baseInit_judge[i]        = false;
  }

  // —— 果酱/糖路跨轮标志 —— 
  for (uint8_t i=0; i<14; ++i) {
    //jamRanThisCycle[i]   = false;
    sugarActive[i]       = false;
  }
  // 糖路计时复位
  for (uint8_t i=0; i<14; ++i) {
    sugarStartMs[i]      = 0;
    sugarStopMs[i]       = 0;
  }

  // —— 阈值与和量（保持补偿表不变） —— 
  liquidsTargetSum         = 0;
  liquidsTargetSumAbs      = 0;
  liquidsCompSum           = 0;
  liquidsThresholdAbs      = 0;
  liquidsStageThresholdAbs = 0;

  totalTargetWeight        = 0;
  totalTargetWeight_pre    = 0;
  // totalBaselineWeight 留给后续按照当前 Weights[] 重新采集
  postIceWeightBaseline    = 0;

  // —— 电机总体态 —— 
  allMotorsInactive        = true;

}

// ========= 硬复位：把能影响流程的变量全部还原到“初始定义值” =========
void resetAllToInitialState() {
  // —— 通讯/缓冲 —— 
  pendingSlaveCmd[0] = '\0';
  deferredSlaveCmd[0]= '\0';

  hasPendingSlave        = false;
  deferSlaveUntilLift    = false;
  waitForCupLift         = false;

  // —— 流程/判据 —— 
  commandReceived        = false;
  isProcessingCommand    = false;
  totalWeightCheckEnabled= false;

  purgeInProgress        = false;
  purgeDoneThisCycle     = false;
  hasPumpThisCycle       = false;
  hasIceThisCycle        = false;
  hasIceAThisCycle       = false;
  hasIceBThisCycle       = false;
  ice_allow_A            = false;
  ice_allow_B            = false;

  liquidsStageTriggered  = false;
  totalSlowdownTriggered = false;
  totalStopTriggered     = false;

  speed_judge            = 0;    // 按“初次定义值”还原（注意：真正开始一轮时建议再置 1）
  Slowdown_judge         = 0;
  ice_judge              = 0;

  // —— 补偿与阈值/和量 ——（恢复到初始值）
  totalTargetWeight      = 0;
  totalTargetWeight_pre  = 0;
  totalTargetWeight_diff = 20;
  totalBaselineWeight    = 0;

  liquidsTargetSum         = 0;
  liquidsTargetSumAbs      = 0;
  liquidsCompSum           = 0;
  liquidsThresholdAbs      = 0;
  liquidsStageThresholdAbs = 0;

  // —— 设备态与计时 —— 
  allMotorsInactive        = true;
  for (int i=0; i<deviceCount; ++i) {
    motorActive[i]           = false;
    relayRunning[i]          = false;

    Weights[i]               = 0;
    lastWeights[i]           = 0;
    baselineWeights[i]       = 0;

    targetWeights[i]         = 0;
    weightDiff[i]            = 0;

    motorStartTime[i]        = 0;
    motorRunDuration[i]      = 0;

    time_check_to_stop[i]    = 0;
    max_time_to_stop[i]      = 0;
    last_time_check_to_stop[i]=0;

    isRecordingDischarge[i]  = false;
    beforeDischargeWeights[i]= 0;
    afterDischargeWeights[i] = 0;
    actualDischargeAmounts[i]= 0;

    baseInit_judge[i]        = false;
  }

  // —— 果酱/糖路 —— 
  for (uint8_t i=0; i<14; ++i) {
    jamRanThisCycle[i] = false;
    sugarActive[i]     = false;
    sugarStartMs[i]    = 0;
    sugarStopMs[i]     = 0;
  }

  // —— 恢复补偿表到“最初定义” —— 
  { // target_diff 初始（A..X 共 24 路）
    int init_target_diff[] = {0,0,28,27,25,25,23,22,21,20,19,22,22,21,23,26,23,22,26,24,0,0,0,0};
    for (int i=0; i<deviceCount && i<(int)(sizeof(init_target_diff)/sizeof(init_target_diff[0])); ++i)
      target_diff[i] = init_target_diff[i];
  }
  { // liquid_diff 初始：{0,0,0,0,0,0,0,0,0,0,0}
    int init_liquid_diff[] = {0,0,0,0,0,0,0,0,0,0,0};
    for (int i=0; i<deviceCount && i<(int)(sizeof(init_liquid_diff)/sizeof(init_liquid_diff[0])); ++i)
      liquid_diff[i] = init_liquid_diff[i];
  }

  // —— 其它 —— 
  postIceWeightBaseline = 0;
  relayBusFreeAt        = 0;

  // —— RFID（如果使用到） —— 
  uidLen = 0; lastUidLen = 0; hasCard = false; hasReadCurrentCard = false;
  for (int i=0;i<7;++i){ uid[i]=0; lastUid[i]=0; }
}

// 碎冰接近开关中断（高电平有效）
void IRAM_ATTR encoder1ISR() {
  const uint32_t nowUs = micros();
  if (nowUs - crushLastPulseUs < CRUSH_MIN_PULSE_INTERVAL_US) {
    return; // 软防抖：忽略毛刺/抖动
  }
  crushLastPulseUs = nowUs;
  encoderCount1++;
  encoderTotal1++;
}

// 螺旋杆霍尔编码器中断（上升沿有效）
void IRAM_ATTR encoder2ISR() {
  const uint32_t nowUs = micros();
  if (nowUs - augerLastPulseUs < AUGER_MIN_PULSE_INTERVAL_US) {
    return; // 软防抖：忽略毛刺/抖动
  }
  augerLastPulseUs = nowUs;
  encoderCount2++;
  encoderTotal2++;
}

// 搅动电机接近式开关 ISR（GPIO35，高电平有效）
void IRAM_ATTR stirEncoderISR() {
  const uint32_t nowUs = micros();
  if (nowUs - stirLastPulseUs < STIR_MIN_PULSE_INTERVAL_US) {
    return; // 软防抖：忽略毛刺/抖动
  }
  stirLastPulseUs = nowUs;
  stirEncoderCount++;
  stirEncoderTotal++;
}

// 清洁主泵流量计 ISR（GPIO27，上升沿有效）
void IRAM_ATTR cleanFlowISR() {
  cleanFlowPulseCount++;
  cleanFlowLastPulseMs = millis();
}

// ===== PATCH: 搅动电机“卡住反转/换向脱困”检测 =====
// 触发条件：搅动电机处于运行（stirMotorDir!=0）但在多个窗口内无脉冲
void checkStirMotorStall() {
  static unsigned long lastCheck = 0;
  static uint8_t stallWin = 0;
  const unsigned long now = millis();
  const unsigned long WIN_MS = 150;     // 检测窗口
  const uint8_t NEED_STALL_WINS = 5;    // 连续 N 个窗口无脉冲 -> 认为卡住
  const unsigned long ESCAPE_MS = 600;  // 脱困换向持续时间

  if (now - lastCheck < WIN_MS) return;
  lastCheck = now;

  if (stirMotorDir == DIR_STOP) {
    stallWin = 0;
    noInterrupts();
    stirEncoderCount = 0;
    interrupts();
    return;
  }

  long pulses;
  noInterrupts();
  pulses = stirEncoderCount;
  stirEncoderCount = 0;
  interrupts();

  const bool moving = (pulses > 0);
  if (moving) {
    stallWin = 0;
    return;
  }

  if (++stallWin < NEED_STALL_WINS) return;
  stallWin = 0;

  // 卡住：按当前方向进行“反向/换向脱困”
  const int8_t prevDir = stirMotorDir;
  Serial.println("[STIR] stall -> escape");
  stirMotorStop();
  delay(80);
  if (prevDir == DIR_FWD) {
    // 正转卡住 -> 反转脱困
    stirMotorReverse();
  } else {
    // 反转卡住（通常是空闲搅冰） -> 改为正转摆脱
    stirMotorForward();
  }
  delay(ESCAPE_MS);
  stirMotorStop();
  delay(80);
  // 恢复原方向
  if (prevDir == DIR_FWD) stirMotorForward();
  else if (prevDir == DIR_REV) stirMotorReverse();
}

// ===== PATCH: 碎冰电机（冰机）卡住脱困检测 =====
// 触发条件：冰机处于运行（iceMotorDir!=0）但在多个窗口内无编码器脉冲
void checkCrushedIceMotorStall() {
  static unsigned long lastCheck = 0;
  static uint8_t stallWin = 0;
  const unsigned long now = millis();
  const unsigned long WIN_MS = 150;
  const uint8_t NEED_STALL_WINS = 5;
  const unsigned long ESCAPE_MS = 800;

  if (now - lastCheck < WIN_MS) return;
  lastCheck = now;

  if (iceMotorDir == DIR_STOP) {
    stallWin = 0;
    noInterrupts();
    encoderCount1 = 0;
    interrupts();
    return;
  }

  long pulses;
  noInterrupts();
  pulses = encoderCount1;
  encoderCount1 = 0;
  interrupts();

  const bool moving = (pulses > 1);
  if (moving) {
    stallWin = 0;
    return;
  }

  if (++stallWin < NEED_STALL_WINS) return;
  stallWin = 0;

  const int8_t prevDir = iceMotorDir;
  Serial.println("[ICE] stall -> reverse escape");
  iceMotorStop();
  delay(80);
  // 按你需求：卡住优先“反转摆脱”。若当前本就在反转，则改为正转摆脱。
  if (prevDir == DIR_FWD) iceMotorReverse();
  else iceMotorForward();
  delay(ESCAPE_MS);
  iceMotorStop();
  delay(80);
  // 恢复原方向
  if (prevDir == DIR_FWD) iceMotorForward();
  else if (prevDir == DIR_REV) iceMotorReverse();
}

// ===== 新版：基于两路接近 + 一路霍尔的卡死检测（反转3s -> 正转3s，最多3遍，失败停机） =====
static inline long readTotalSafe(volatile long* p) {
  long v;
  noInterrupts();
  v = p ? *p : 0;
  interrupts();
  return v;
}

static void stopIceAllWithPopup(const char* tag) {
  // 统一停机（冰机/搅冰/传送带）
  iceMotorStop();
  augerMotorStop();
  stirMotorStop();
  // 同步逻辑状态
  stopMotor(IDX_CRUSHED);
  stopMotor(IDX_ICE);
  speed_judge = 0;
  Serial.print("POPUP:");
  Serial.println(tag);
}

struct StallRecover {
  const char* tag = "M";
  volatile long* total = nullptr;
  uint8_t minPulses = 1;
  uint8_t needWins  = 5;
  uint32_t winMs    = 150;
  uint32_t phaseMs  = 3000;
  uint8_t maxCycles = 3;

  long     lastTotal = 0;
  uint32_t lastWinMs = 0;
  uint8_t  noPulseWins = 0;

  enum Phase : uint8_t { IDLE=0, REV=1, FWD=2 } phase = IDLE;
  uint32_t phaseStartMs = 0;
  long     phaseStartTotal = 0;
  uint8_t  cycles = 0;
};

static StallRecover stallCrush;
static StallRecover stallAuger;
static StallRecover stallStir;

static inline void stallReset(StallRecover& m) {
  m.lastTotal = 0;
  m.lastWinMs = 0;
  m.noPulseWins = 0;
  m.phase = StallRecover::IDLE;
  m.phaseStartMs = 0;
  m.phaseStartTotal = 0;
  m.cycles = 0;
}

static inline void enterRev(StallRecover& m, uint32_t nowMs,
                            void (*doRev)()) {
  if (doRev) doRev();
  m.phase = StallRecover::REV;
  m.phaseStartMs = nowMs;
  m.phaseStartTotal = readTotalSafe(m.total);
}

static inline void enterFwd(StallRecover& m, uint32_t nowMs,
                            void (*doFwd)()) {
  if (doFwd) doFwd();
  m.phase = StallRecover::FWD;
  m.phaseStartMs = nowMs;
  m.phaseStartTotal = readTotalSafe(m.total);
}

static void handleStall(StallRecover& m, bool running, uint32_t nowMs,
                        void (*doFwd)(), void (*doRev)()) {
  if (!running) {
    stallReset(m);
    return;
  }

  // 处于脱困流程
  if (m.phase != StallRecover::IDLE) {
    if (nowMs - m.phaseStartMs >= m.phaseMs) {
      if (m.phase == StallRecover::REV) {
        enterFwd(m, nowMs, doFwd);
      } else if (m.phase == StallRecover::FWD) {
        const long cur = readTotalSafe(m.total);
        const long dp = cur - m.phaseStartTotal;
        if (dp >= m.minPulses) {
          // 已恢复
          stallReset(m);
          return;
        }
        // 未恢复：进入下一轮
        if (++m.cycles >= m.maxCycles) {
          stopIceAllWithPopup("ICE_STALL");
          stallReset(m);
          return;
        }
        enterRev(m, nowMs, doRev);
      }
    }
    return;
  }

  // 正常监测：窗口内无脉冲则计数
  if (m.lastWinMs == 0) {
    m.lastWinMs = nowMs;
    m.lastTotal = readTotalSafe(m.total);
    return;
  }
  if (nowMs - m.lastWinMs >= m.winMs) {
    const long cur = readTotalSafe(m.total);
    const long dp = cur - m.lastTotal;
    m.lastTotal = cur;
    m.lastWinMs = nowMs;
    if (dp >= m.minPulses) {
      m.noPulseWins = 0;
      return;
    }
    if (++m.noPulseWins >= m.needWins) {
      m.noPulseWins = 0;
      m.cycles = 0;
      enterRev(m, nowMs, doRev);
    }
  }
}

static void checkIceStallRecoveryNew() {
  const uint32_t nowMs = millis();
  const bool crushRun = motorActive[IDX_CRUSHED];
  const bool stirRun  = motorActive[IDX_ICE];
  const bool augerRun = (motorActive[IDX_CRUSHED] || motorActive[IDX_ICE]);

  handleStall(stallCrush, crushRun, nowMs, iceMotorForward,  iceMotorReverse);
  handleStall(stallStir,  stirRun,  nowMs, stirMotorForward, stirMotorReverse);
  handleStall(stallAuger, augerRun, nowMs, augerMotorForward, augerMotorReverse);
}

// 封装好的检测函数：在 loop() 里反复调用
void checkMotorsMoving() {
  static unsigned long lastCheckTime = 0;

  unsigned long now = millis();
  if (now - lastCheckTime < CHECK_INTERVAL_MS) {
    return;  // 时间未到，直接返回
  }
  

  // 读取并清零两个电机在本时间窗口内的计数
  long c1, c2, c3;
  noInterrupts();
  c1 = encoderCount1;
  c2 = encoderCount2;
  c3 = stirEncoderCount;
  encoderCount1 = 0;
  encoderCount2 = 0;
  stirEncoderCount = 0;
  interrupts();

  bool moving1 = (c1 > 1);
  bool moving3 = (c3 > 1);
  bool moving2 = (c2 > 3);
  // Serial.println("---------------");
  // Serial.println(moving1);
  // Serial.println(moving2);
  // Serial.println("---------------");

  // 串口输出状态
  // Serial.print("M1: ");
  // Serial.print(moving1 ? "MOVING" : "STOP");
  // Serial.print("  |  M2: ");
  // Serial.println(moving2 ? "MOVING" : "STOP");
  if(motorActive[0]&&motorActive[1]&&speed_judge){//都为运行状态
    if(moving1==1&&moving3==1&&moving2==0){//搅冰和碎冰转,螺旋杆不转
      vTaskSuspend(weightReadTaskHandle);
      lock_judge=1;
      relayWrite(relayOffCmd_3[3],8);
      delay(50);
      relayWrite(relayOffCmd_3[4],8);//关闭碎冰
      delay(50);
      relayWrite(relayOffCmd_ICE_STIR_FWD,8);
      delay(50);
      relayWrite(relayOffCmd_ICE_STIR_REV,8);//关闭搅冰
      delay(50);
      Serial.println("ice_out_locking");
      
      //执行螺旋杆堵的操作//
      //  ...........................//
      //

    }
    else if(moving1==0&&moving3==1&&moving2==1){//碎冰不转,搅冰转，螺旋杆转
      vTaskSuspend(weightReadTaskHandle);
      lock_judge=1;
      relayWrite(relayOffCmd_3[3],8);
      delay(50);
      relayWrite(relayOffCmd_3[4],8);//关闭碎冰
      delay(50);
      Serial.println("crushed_ice_locking");
      delay(1000);
      //执行碎冰堵的操作//
      for(int i=0;i<3;i++){
        relayWrite(relayOnCmd_3[3],8);//正转碎冰
        delay(1000);
        relayWrite(relayOffCmd_3[3],8);//关闭碎冰
        delay(50);
        relayWrite(relayOnCmd_3[4],8);//反转碎冰
        delay(1000);
        relayWrite(relayOffCmd_3[4],8);//关闭碎冰
        delay(50);
      }  
    }
    else if(moving1==1&&moving3==0&&moving2==1){//碎冰转,搅冰bu转，螺旋杆转
      vTaskSuspend(weightReadTaskHandle);
      lock_judge=1;
      relayWrite(relayOffCmd_ICE_STIR_FWD,8);
      delay(50);
      relayWrite(relayOffCmd_ICE_STIR_REV,8);//关闭搅冰
      delay(50);
      Serial.println("crushed_ice_locking");
      delay(1000);
      //执行jiao冰堵的操作//
      for(int i=0;i<3;i++){
        relayWrite(relayOnCmd_ICE_STIR_FWD,8);//正转jiao冰
        delay(1000);
        relayWrite(relayOffCmd_ICE_STIR_FWD,8);//关闭jiao冰
        delay(50);
        relayWrite(relayOnCmd_ICE_STIR_REV,8);//反转jiao冰
        delay(1000);
        relayWrite(relayOffCmd_ICE_STIR_REV,8);//关闭jiao冰
        delay(50);
      }  
    }
    else if(moving1==0&&moving3==0&&moving2==0){//冰机不转,螺旋杆不转
      vTaskSuspend(weightReadTaskHandle);
      lock_judge=1;
      for(int i=0;i<5;i++){
        relayWrite(relayOffCmd_3[i],8);
        delay(50);
        relayWrite(relayOffCmd_ICE_STIR_FWD,8);
        delay(50);
        relayWrite(relayOffCmd_ICE_STIR_REV,8);//关闭搅冰
        delay(50);
      }
      Serial.println("locking");
      //执行冰机堵和螺旋杆堵的操作//
      //  ...........................//
      //
    }
    if (lock_judge == 1) {
      lock_judge = 0;
      // 1. 先执行你的解堵动作
      relayWrite(relayOffCmd_3[4], 8); 
      delay(50);
      relayWrite(relayOnCmd_3[3], 8); // 开启碎冰
      delay(50);
      relayWrite(relayOffCmd_ICE_STIR_REV,8);//搅冰反转关闭
      delay(50);
      relayWrite(relayOnCmd_ICE_STIR_FWD,8);//搅冰正转开启
      delay(50);
      relayWrite(relayOnCmd_3[0], 8);
      delay(50);
      relayWrite(relayOffCmd_3[1], 8); // 开启传送带

      // 2. 清零编码器计数，准备“观察窗口”
      noInterrupts();
      encoderCount1 = 0;
      encoderCount2 = 0;
      stirEncoderCount = 0;
      interrupts();

      // 3. 给一点时间让电机实际转动（这段时间内中断会不断累加计数）
      delay(100);  // 这里不需要 5000ms，500ms 一般就够判断是不是在转

      // 4. 读取这段时间内的脉冲数，并清零（下次用）
  long c1_after, c2_after, c3_after;
      noInterrupts();
      c1_after = encoderCount1;
      c2_after = encoderCount2;
      c3_after = stirEncoderCount;
      // Serial.println(encoderCount1);
      // Serial.println(encoderCount2);
      encoderCount1 = 0;
      encoderCount2 = 0;
      stirEncoderCount = 0;
      interrupts();
      

      bool moving1_after = (c1_after > 4);
      bool moving3_after = (c3_after > 4);
      bool moving2_after = (c2_after > 7);

      if (moving1_after && moving2_after && moving3_after) {
        Serial.println("unlock_finish");   // 建议 println，避免和上一行粘在一起
        delay(500);
      } else {
        for (int i = 0; i < 5; i++) {
          relayWrite(relayOffCmd_3[i], 8);
          delay(50);
          relayWrite(relayOffCmd_ICE_STIR_FWD,8);
          delay(50);
          relayWrite(relayOffCmd_ICE_STIR_REV,8);//关闭搅冰
          delay(50);
        }
        stopMotor(1);
        stopMotor(0);
        speed_judge = 0;
        Serial.println("locked");
      }
      vTaskResume(weightReadTaskHandle);
    }
  }
  lastCheckTime = now;
}


// 带最小间隔的安全发送；返回 true 表示本次帧已经成功发出
inline bool trySendRelay(const uint8_t* frame, size_t len, uint16_t min_gap_ms = 25) {
  uint32_t now = millis();
  if (now < relayBusFreeAt) return false;
  relayWrite(frame, len);
  relayBusFreeAt = now + min_gap_ms;  // 锁总线，留出硬件处理时间
  return true;
}


inline void checkIceJude() {
  // 仅当 motorActive[0]==1 且 motorActive[1]==1，且其余全为 0 时，将 ice_jude 置 1
  if (motorActive[0] == 1 && motorActive[1] == 1) {
    for (uint8_t i = 2; i < deviceCount; ++i) {
      if (motorActive[i] != 0) return;   // 发现其它有 1，直接退出
    }
    // ice_judge = 1;
  }
}

void checkCupLiftTrigger() {  //拿杯出小料判定逻辑
  if (!(deferSlaveUntilLift && waitForCupLift && deferredSlaveCmd[0] != '\0')) 
    return;

  int32_t cur = Weights[deviceCount-1]; // 总重量
  if (cur == INVALID_WEIGHT) 
  {
    return;
  }

  int32_t drop = postIceWeightBaseline - cur;  // 下降量
  if (drop >= LIFT_DROP_THRESHOLD) {
    if (liftDropStart == 0) {
      liftDropStart = millis();
    } else if (millis() - liftDropStart >= LIFT_DEBOUNCE_MS) {
      // 满足条件：发给小料机
      strncpy(dataS1.command, deferredSlaveCmd, sizeof(dataS1.command)-1);
      dataS1.command[sizeof(dataS1.command)-1] = '\0';
      esp_now_send(slaveMac1, (uint8_t*)&dataS1, sizeof(dataS1));

      // 清理状态
      deferredSlaveCmd[0] = '\0';
      deferSlaveUntilLift = false;
      waitForCupLift = false;
      liftDropStart = 0;
    }
  } else {
    liftDropStart = 0; // 去抖复位
  }
}



inline bool isLiquid(uint8_t i) {        // ← 覆盖原定义
  return (i >= LIQ_START && i <= LIQ_END);
}

inline bool allLiquidsStopped() {
  for (uint8_t i = LIQ_START; i <= LIQ_END; ++i) {
    if (motorActive[i]) return false;
  }
  return true;
}


bool arrayHasData(int32_t array[], int Length) {   //判断数组是否异常
  for (int i = 0; i < Length; i++) {
    if (array[i] != 0 && array[i] != INVALID_WEIGHT) {  // 假设数据为非零时有效
      return true;
    }
  }
  return false;
}
// 解析Modbus RTU消息
ModbusParsedData parse_modbus_message(uint8_t *buffer, size_t length) {
  ModbusParsedData data = {0};
  if (length < 9) {  // 最小响应长度调整为8字节
    // Serial.println("Error: Message too short");
    return data;
  }
  
  // 校验CRC 
  uint16_t received_crc = (buffer[length - 1] << 8) | buffer[length - 2]; 
  uint16_t calculated_crc = calculate_crc(buffer, length - 2);
  if (received_crc != calculated_crc) {
    // Serial.println("Error: CRC mismatch");
    return data;
  }
  
  // 解析各字段
  data.slave_id = buffer[0];
  data.function_code = buffer[1];
  data.byte_count = buffer[2];
  
  // 根据实际数据格式修改 (示例数据: 01 03 04 06 0a 00 00 da b9)
  // 寄存器数据为2个16位寄存器 (4字节)，大端序
  data.register1 = (buffer[3] << 8) | buffer[4];  // 第一个寄存器的值
  data.register2 = (buffer[5] << 8) | buffer[6];  // 第二个寄存器的值
  
  return data;
}
// 计算Modbus CRC16校验
uint16_t calculate_crc(uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; i++) {
    crc ^= data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x0001) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  return crc;
}
// 发送Modbus请求 (根据示例修改)
void send_modbus_request(uint8_t slave_id, uint8_t function_code, uint8_t high_addr, uint8_t low_addr, uint16_t num_regs) {
  uint8_t request[8];

  request[0] = slave_id;
  request[1] = function_code;
  request[2] = high_addr & 0xFF;  // 起始地址高字节
  request[3] = low_addr & 0xFF;         // 起始地址低字节
  request[4] = (num_regs >> 8) & 0xFF;    // 寄存器数量高字节
  request[5] = num_regs & 0xFF;           // 寄存器数量低字节
  
  // 计算CRC
  uint16_t crc = calculate_crc(request, 6);
  
  request[6] = crc & 0xFF;    // CRC低字节
  request[7] = (crc >> 8) & 0xFF; // CRC高字节
  
  // Serial.print("获取重量的原始命令: ");
  // for (int i = 0; i < 8; i++) {
  //     if (request[i] < 0x10) Serial.print("0"); // 补零（如 0x0A → "0A"）
  //     Serial.print(request[i], HEX);
  //     Serial.print(" ");
  // }
  // Serial.println();

  SerialWeight.write(request, 8);
}
// 称重读取任务（不使用ModbusMaster库）
void weightReadTask(void *pvParameters) {
  uint8_t response[20];
  size_t response_length;
  int j = 0;
  uint16_t start = 0x0000;           // 起始寄存器
  while (1) {
    for (uint8_t i = 0; i < deviceCount; i++) {

      // ===== PATCH: 糖(U/V) 与 水(W) 采用“按时间关断”，不参与称重读取 =====
      if ((isSugarIdx(i) || isWaterIdx(i)) && motorActive[i] && sugarActive[i]) {
        if ((millis() - sugarStartMs[i]) >= sugarStopMs[i]) {
          Serial.println("🟡 糖/水计时到，停止");
          motorActive[i]   = false;
          baseInit_judge[i]= false;
          sugarActive[i]   = false;
          sugarStartMs[i]  = 0;
          sugarStopMs[i]   = 0;
          Weights[i]       = 999;

            if (isSugarIdx(i)) {
              // U / V 停止：B/C都关
              bool isU = (i == SUG_START);
              sugarSetState(isU, true, SUGAR_OFF);
            } else {
              // 水停止：如 relayOffCmd[IDX_WATER] 已配置则会生效
              relayWrite(relayOffCmd[i], 8);
              delay(50);
            }
        }
        continue; // 糖/水：不读重量
      }
      if (allMotorsInactive == false || isTotalIdx(i)) {    // 状态判断：活跃 或 非活跃
        if (motorActive[i] == true || isTotalIdx(i)) {      // 电机（管路）判断：活跃 或 非活跃
          if (i == 0){
            Weights[i] = Weights[i+1];
            continue;
          }
          SerialWeight.flush(); // 清空发送缓冲区
          while(SerialWeight.available()) SerialWeight.read(); // 清空接收缓冲区
          addr = deviceAddresses[i];
          // Serial.print("num_j:");Serial.println(j);
          if (addr == 0x01) {
            start = isTotalIdx(i) ? 0x02 : 0x00;
            addr_2 = start;
            send_modbus_request(addr, 0x03, 0x00, start, 0x0002);
          }else if(addr == 0x02){
            addr_2 = addresses[i - LIQ_START];
            send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);   // 发送读取请求   // 发送读取请求 fa
          } else if (addr == 0x05) {
            // 果酱 C/D/E/F（索引 2..5）映射到 0x05 的第2/3/4/5位寄存器偏移
            uint8_t j = i - JAM_START;
            if (j < 4) {
              addr_2 = jam_offsets[j];
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            } else {
              addr_2 = 0x00;
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            }
          }
          else if(addr == LIQUID_4CH_ADDR){
            // 新增4路称重模块：液体13/14（索引18/19）
            uint8_t k = i - LIQ_4CH_START; // 0或1
            if (k < 2) {
              addr_2 = liq4ch_offsets[k];
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            } else {
              // 越界保护（理论不会进入）
              addr_2 = 0x00;
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            }
          }
          // 等待响应
          unsigned long startWait = millis();
          while (SerialWeight.available() < 8 && millis() - startWait < 5) {
            vTaskDelay(1 / portTICK_PERIOD_MS);
          }
          response_length = SerialWeight.readBytes(response, sizeof(response));
          
          if (response_length >= 8) { // 最小有效响应长度
            // 解析Modbus消息
            ModbusParsedData parsed = parse_modbus_message(response, response_length);
            if (parsed.slave_id == addr && parsed.function_code == 0x03) {
              // 处理寄存器1数据
              int32_t currentWeight = (int16_t)parsed.register1; 

              if (lastWeights[i] == 0) {
                Weights[i] = currentWeight;
              } else if (lastWeights[i] <= 100000 && lastWeights[i] >= 1) {
                
                Weights[i] = currentWeight;
              } else {
                // Serial.print("lastWeights异常:");
                // Serial.println(lastWeights[i]);
                lastWeights[i] = currentWeight;
                Weights[i] = currentWeight;
                
              }
              // if (currentWeight != lastWeights[i]) {
                if (addr==254 && addr_2==254) {
                  // Serial.print(addr);
                  // Serial.print(".");
                  // Serial.print(addr_2);
                  // Serial.print(" index:");
                  // Serial.print(i);
                  // Serial.print(" originalWeight:");
                  // Serial.print(currentWeight);
                  // Serial.print("; lastWeight:");
                  // Serial.print(lastWeights[i]);
                  // Serial.print("; smoothedWeight:");
                  // Serial.println(Weights[i]); 
                }
                
                lastWeights[i] = Weights[i];
              // }
            }
          } else if (response_length > 0) {
            // Serial.print(addr);
            // Serial.print(".");
            // Serial.print(addr_2);
            // Serial.print(" 响应长度不足:");
            // Serial.println(response_length);
          }
          
          vTaskDelay(2 / portTICK_PERIOD_MS);
        }
      }
      else {
        // 在每次发送请求前添加
          SerialWeight.flush(); // 清空发送缓冲区
          while(SerialWeight.available()) SerialWeight.read(); // 清空接收缓冲区
          addr = deviceAddresses[i];

          if (addr == 0x01) {
            start = isTotalIdx(i) ? 0x02 : 0x00;
            addr_2 = start;
            send_modbus_request(addr, 0x03, 0x00, start, 0x0002);
          }else if(addr == 0x02){
            addr_2 = addresses[i - LIQ_START];
            send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);   // 发送读取请求   // 发送读取请求 fa
          } else if (addr == 0x05) {
            // 果酱 C/D/E/F（索引 2..5）映射到 0x05 的第2/3/4/5位寄存器偏移
            uint8_t j = i - JAM_START;
            if (j < 4) {
              addr_2 = jam_offsets[j];
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            } else {
              addr_2 = 0x00;
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            }
          }
          else if(addr == LIQUID_4CH_ADDR){
            // 新增4路称重模块：液体13/14（索引18/19）
            uint8_t k = i - LIQ_4CH_START; // 0或1
            if (k < 2) {
              addr_2 = liq4ch_offsets[k];
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            } else {
              // 越界保护（理论不会进入）
              addr_2 = 0x00;
              send_modbus_request(addr, 0x03, 0x00, addr_2, 0x0002);
            }
          }
          response_length = SerialWeight.readBytes(response, sizeof(response));
          // Serial.print("原始重量数据: ");
          // for (int i = 0; i < 9; i++) {
          //   if (response[i] < 0x10) Serial.print("0"); // 补零（如 0x0A → "0A"）
          //   Serial.print(response[i], HEX);
          //   Serial.print(" ");
          // }
          // Serial.println();
          if (response_length >= 8) { // 最小有效响应长度
            ModbusParsedData parsed = parse_modbus_message(response, response_length);
            if (parsed.slave_id == addr && parsed.function_code == 0x03) {
              // 处理寄存器1数据
              int32_t currentWeight = (int16_t)parsed.register1; 
              if (lastWeights[i] == 0) {
                Weights[i] = currentWeight;
              } else if (lastWeights[i] <= 100000 && lastWeights[i] >= 1) {
                // Weights[i] = (int32_t)(currentWeight * alpha[i] + lastWeights[i] * (1.0f - alpha[i]));
                Weights[i] = currentWeight; //不使用平滑算法
              } else {
                // Serial.print("lastWeights异常:");
                // Serial.println(lastWeights[i]);
                lastWeights[i] = currentWeight;
                Weights[i] = currentWeight;
              }
              if (currentWeight != lastWeights[i]) {
                // Serial.print(addr);
                // Serial.print(".");
                // Serial.print(addr_2);
                // Serial.print(" originalWeight:");
                // Serial.print(currentWeight);
                // Serial.print("; lastWeight:");
                // Serial.print(lastWeights[i]);
                // Serial.print("; smoothedWeight:");
                // Serial.println(Weights[i]); 
                lastWeights[i] = Weights[i];
              }
            }
          } else if (response_length > 0) {
            // Serial.print(addr);
            // Serial.print(".");
            // Serial.print(addr_2);
            // Serial.print(" 响应长度不足:");
            // Serial.println(response_length);
          }
          vTaskDelay(10 / portTICK_PERIOD_MS);
      }  
      
    }

    // 这里注释调的是发送python界面的代码，python程序要识别这些才能获得重量信息
    if (arrayHasData(Weights, deviceCount)) { // 检查数组是否有数据
      Serial.print("wD:");
      for (int i = 0; i < deviceCount; i++) {
        Serial.print(Weights[i]);
        if (i < deviceCount-1) {
          Serial.print(", ");
        }
      }
      Serial.println();
    }
    Serial.print("mA:");
    for (int i = 0; i < deviceCount; i++) {
      Serial.print(motorActive[i]);
      if (i < deviceCount-1) {
        Serial.print(", ");
      }
    }
    Serial.println();  

    if (allMotorsInactive == false) {
      vTaskDelay(1 / portTICK_PERIOD_MS);
    }else {
      vTaskDelay(300 / portTICK_PERIOD_MS);
    }
    
  }
}
void addPeer(const uint8_t* peerMac) {
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, peerMac, 6);
  peerInfo.channel = 1;  // 使用默认频道
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    // Serial.print("Failed to add peer: ");
    printMacAddress(peerMac);
  }
  else {
    // Serial.print("Peer added successfully: ");
    printMacAddress(peerMac);
  }
}
//打印给定 MAC 地址的十六进制格式。
void printMacAddress(const uint8_t* mac) {
    for (int i = 0; i < 6; i++) {
      // Serial.print(mac[i], HEX);
      // if (i < 5) Serial.print(":");
    }
    // Serial.println();
}
// 发送数据后的回调函数
void onDataSent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  // Serial.print("Last Packet Send Status: ");
  // Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

static void onDataRecv(const esp_now_recv_info_t* info,const uint8_t* data, int len) {
  if (len == sizeof(struct_message)) {
    struct_message rx{};
    memcpy(&rx, data, sizeof(rx));
    Serial.printf("%.*s\n", (int)sizeof(rx.command), rx.command);
  } else {
    // 长度不匹配就按字节打印
    for (int i=0;i<len;i++) Serial.write(data[i]);
    Serial.println();
  }
}

void stopMotor(int motorIndex) {
  // ===== PATCH: A(冰)/B(碎冰) 通道停止时，必须关闭冰机与传送带等关联继电器 =====
  // 说明：A/B 的启动逻辑使用 relayOnCmd_3[3]/[4]（冰机正反）+ relayOnCmd_3[0]/relayOffCmd_3[1]（传送带）。
  // 原 stopMotor() 走 relayOffCmd[motorIndex] 可能无法真正停掉冰机，因此在此加专用停机。
  if (motorIndex == IDX_ICE) {
    // A 通道（搅冰电机 7/8）：只停 fsmStir，避免误停 B
    fsmStir.forceStop();
    motorActive[motorIndex] = false;
    finalizeStopMotorCommon(motorIndex);
    return;
  }
  if (motorIndex == IDX_CRUSHED) {
    // B 通道（碎冰电机 3/4）：只停 fsmCrush，避免误停 A
    fsmCrush.forceStop();
    motorActive[motorIndex] = false;
    finalizeStopMotorCommon(motorIndex);
    return;
  }

  if (isJamIdx(motorIndex)) {
      if(motorActive[motorIndex]){
      relayWrite(relayOffCmd_4[(motorIndex-2)*2], 8, 30);//2--0,1    3--2,3    4--4,5
      relayWrite(relayOffCmd_4[(motorIndex-2)*2+1], 8, 30);//2--0,1    3--2,3    4--4,5

      }
  }
  else{
  // —— 非果酱通道：维持原来的“立即关闭”逻辑 ——
    relayWrite(relayOffCmd[motorIndex], 8);
    motorActive[motorIndex]     = false;
    delay(30);
  }

  // 把下面这段重构成一个公共函数，供普通停机和果酱序列完成后复用
  finalizeStopMotorCommon(motorIndex);
}

void finalizeStopMotorCommon(int motorIndex) {
  if (motorIndex == 0) {
    // 停传送带从机
    // strncpy(myData.command, "stop", sizeof(myData.command) - 1);
    // myData.command[sizeof(myData.command) - 1] = '\0';
    // esp_now_send(slaveMac2, (uint8_t*)&myData, sizeof(myData));
  }

  relayRunning[motorIndex] = false;
  time_check_to_stop[motorIndex] = 0;
  max_time_to_stop[motorIndex] = 0;
  motorActive[motorIndex] = false;
  baseInit_judge[motorIndex] = false;
  targetWeights[motorIndex] = 0;
  baselineWeights[motorIndex] = 0;
  weightDiff[motorIndex] = 0;
  isRecordingDischarge[motorIndex] = true;
  dischargeCompleteTime[motorIndex] = millis();
  lastUpdateTime = 0;

  purgeInProgress = false;
  purgeDoneThisCycle = false;
  hasPumpThisCycle = false;

  // for (uint8_t i = JAM_START; i <= JAM_END; ++i) jamRanThisCycle[i] = false;

  iceStatus[motorIndex].accumulatedArea = 0;
  iceStatus[motorIndex].pointsInWindow1 = 0;
  iceStatus[motorIndex].pointsInWindow2 = 0;
  iceStatus[motorIndex].lastUpdateTime  = 0;
}


inline bool allPumpsStopped() {
  for (uint8_t i = JAM_START; i <= IDX_WATER; ++i) {
    if (motorActive[i]) return false;
  }
  return true;
}

void checkTotalWeight() {
  // Serial.print("totalWeightCheckEnabled:");
  // Serial.println(totalWeightCheckEnabled);
  // ① 当所有泵（果酱+水路）都停：先顺序反转果酱
  if (allPumpsStopped() && !purgeDoneThisCycle && !purgeInProgress) {
    Serial.println("进入反转");
    purgeJamsSequential();
  }

  // ② 放冰：
  //    - 如果这轮有冰任务：等到所有泵停（并已触发/或无需触发反转）就放行；
  //    - 如果这轮没有泵任务（例如 A100 B100），一开始 allPumpsStopped() 就是 true ⇒ 直接放行。
  // Serial.printf("hasICe:%d\r\n",hasIceThisCycle);
  // Serial.printf("all:%d\r\n",allPumpsStopped());
  if (hasIceThisCycle && allPumpsStopped()&&purgeDoneThisCycle) {
    ice_judge = 1;  // 冰流程放行（A/B分别放行）
    ice_allow_A = hasIceAThisCycle;
    ice_allow_B = hasIceBThisCycle;
  }
  if (!totalWeightCheckEnabled) return;

  lastUpdateTime = millis();

  // 当前总重量增量 = 当前值 - 基线（开始配方时的值）
  int32_t currentTotalWeight = Weights[deviceCount-1]; // 总重量在最后一个通道
  int32_t totalWeightDiff = currentTotalWeight - totalBaselineWeight;

    // —— 第一次阈值（绝对值）：达到“水路总目标量” → 先停水路、放行冰机（新增） ——
    // —— 第一次阈值（绝对值）：达到“∑水路目标 − ∑水路惯性” → 先停所有水路、放行冰机（新增）——
  if (!liquidsStageTriggered && liquidsThresholdAbs > 0 && totalWeightDiff >= liquidsThresholdAbs) {
    // 1) 停止所有水路（不含 A/B/总重）
    
    for (int i = 0; i < deviceCount; i++) {
      if (isLiquid(i) && motorActive[i]) {
        stopMotor(i);
        // SerialRelay.write(relayallOffCmd, 8);
        delay(50);
        // memset(motorActive,0,sizeof(motorActive));
        
        Serial.println("电机停止了…………………………………………………………………………………………………………………………");
        Serial.print("totalWeightDiff:");
        Serial.println(totalWeightDiff);
        Serial.print("liquidsThresholdAbs:");
        Serial.println(liquidsThresholdAbs);
        // finalizeStopMotorCommon(i);
      }
    }
    // ice_judge = 1;
    liquidsStageTriggered=true;
  }


  // 百分比阈值
  const float slowDownThreshold = totalTargetWeight * TOTAL_SLOWDOWN_RATIO+((totalTargetWeight-100)/100)*33; // 67%+补偿值
  const float stopThreshold     = totalTargetWeight * TOTAL_STOP_RATIO+((totalTargetWeight-100)/100)*10;     // 90%+补偿值

  // Serial.print("总重量变化: "); Serial.print(totalWeightDiff); Serial.print("/");
  // Serial.println(totalTargetWeight);
  // Serial.println("冰停：");
  // Serial.println(!totalSlowdownTriggered);
  // Serial.println(totalWeightDiff);
  // Serial.println(slowDownThreshold);
  // Serial.println(speed_judge);
  // 85%：减速传送带（485 指令） totalTargetWeight-33
  if (!totalSlowdownTriggered && totalWeightDiff >= slowDownThreshold&&speed_judge==1) {
  // if (!totalSlowdownTriggered && totalWeightDiff >= (totalTargetWeight-33)&&speed_judge==1) {
    speed_judge=0;  
    Slowdown_judge=1;
    // 传送带减速
    relayWrite(relayOnCmd_3[2], 8);
    delay(50);
    Serial.println("达到 85%：减速传送带 + （保留冰机运行、其他电机按需要处理）");
    relayWrite(relayOffCmd_3[4], 8);
    delay(50);
    relayWrite(relayOffCmd_3[3], 8);
    delay(50);
    relayWrite(relayOffCmd_ICE_STIR_REV,8);//搅冰反转关闭
    delay(50);
    relayWrite(relayOnCmd_ICE_STIR_FWD,8);//搅冰正转开启
    delay(50);
    // SerialRelay.write(relayOffCmd_3[2],8);
    // delay(50);
    stopMotor(13);

    totalSlowdownTriggered = true;
  }

  // 95%：全停（含传送带与冰机）
  if (!totalStopTriggered && totalWeightDiff >= stopThreshold&&Slowdown_judge==1) {
  // if (!totalStopTriggered && totalWeightDiff >= (totalTargetWeight-10)) {
    // ice_judge=1;
    Slowdown_judge=0;

    relayWrite(relayOffCmd_3[1], 8);  // com 置常开
    delay(50);
    relayWrite(relayOffCmd_3[0], 8);  // com 置常开
    delay(50);
    relayWrite(relayOffCmd_3[2], 8);  // com 置常开
    delay(50);
    Serial.println("达到 95%：全停（包含传送带与冰机）");
    // 停止所有仍在运行的电机（冰机停止=串口发 Modbus 指令，封装在 stopMotor 里）
    // for (int i = 0; i < deviceCount; i++) {
    //   if (motorActive[i]) stopMotor(i);
    // }

    totalStopTriggered = true;
    totalWeightCheckEnabled = false; // 本轮结束
    stopMotor(0);
    stopMotor(1);
    hasIceThisCycle  = false;
    // for (int i=0; i<deviceCount; i++) {
    //   stopMotor(i);
    // }
    return; // 已全停，窗口计数法不用继续跑
  }
}


void Task_CheckTotalWeight(void* pv) {
  const TickType_t period = pdMS_TO_TICKS(20);   // 周期改这里
  TickType_t last = xTaskGetTickCount();
  for (;;) {
    checkTotalWeight();                          // 原函数
    vTaskDelayUntil(&last, period);              // 非阻塞“定时器”
  }
}

// === NEW: 顺序反转本轮跑过的果酱（C..E），阻塞式 delay 版本 ===
// 说明：继电器对的索引 j=(i-JAM_START)*2；ON/OFF 命令数组沿用现有 relayOnCmd_4 / relayOffCmd_4
// 依次对“本轮跑过的”果酱 C..E 执行反转 → 回抽 → 复位
static void purgeJamsSequential() {
  if (purgeDoneThisCycle || purgeInProgress) return;



  purgeInProgress = true;
  vTaskSuspend(weightReadTaskHandle);
  for (uint8_t i = JAM_START; i <= JAM_END; ++i) {
    Serial.printf("2果酱通道索引: %d\n", i);
    Serial.printf("2果酱通道: %d\n", jamRanThisCycle[i]);
    if (!jamRanThisCycle[i]) continue;
    Serial.println("顺序反转果酱,,,");

    uint8_t j = (i - JAM_START) * 2;  // 该果酱通道的两只继电器索引


    //delay(50);
    // —— 进入反转方向（如硬件相反，就对调下面两行）——
    relayWrite(relayOnCmd_4[j], 8, 50);
    relayWrite(relayOffCmd_4[j+1], 8, 50);
    Serial.print("进入反转，，，，");

    // —— 保持反转（回抽防滴漏）——
    vTaskDelay(pdMS_TO_TICKS(1000));  // 反转保持更久，肉眼可见
    
    relayWrite(relayOnCmd_4[j], 8, 50);
    relayWrite(relayOffCmd_4[j+1], 8, 50);
    Serial.print("进入反转，，，，");

    // —— 复位停机（确保反转结束后关闭）——
    relayWrite(relayOffCmd_4[j], 8, 50);
    relayWrite(relayOffCmd_4[j+1], 8, 50);

    jamRanThisCycle[i] = false;  // 该路清线完成
  }

  purgeInProgress = false;
  purgeDoneThisCycle = true;
  vTaskResume(weightReadTaskHandle);
}


// void handleSugar999(char chan ) {
//   if(chan=='U'){
//     Serial.println("U通道24V开启");
//     SerialRelay.write(sugarOnCmd[0],8);
//     delay(50);
//     // motorActive[0]=true;
//   }
//   else if(chan=='V'){
//     Serial.println("V通道24V开启");
//     SerialRelay.write(sugarOnCmd[1],8);
//     delay(50);
//     // motorActive[0]=true;
//   }
  //   else if(chan=='W'){
  //   Serial.println("W通道24V开启");
  //   SerialRelay.write(sugarOnCmd[2],8);
  //   delay(50);
  //   // motorActive[0]=true;
  // }

// }

// isU=true 表示 U 路(继电器1/2/3)，isU=false 表示 V 路(继电器4/5/6)
// use24V=true -> 电压继电器 ON；use24V=false -> 电压继电器 OFF
static inline void sugarSetState(bool isU, bool use24V, uint8_t dir) {
  int rV = isU ? 0 : 3;  // 电压继电器：U->#1(索引0), V->#4(索引3)
  int rB = isU ? 1 : 4;  // 方向B：     U->#2(索引1), V->#5(索引4)
  int rC = isU ? 2 : 5;  // 方向C：     U->#3(索引2), V->#6(索引5)

  // 1) 电压选择：ON=24V, OFF=5V（你已确认）
  if (use24V) relayWrite(relayOnCmd_2[rV], 8, 50);
  else        relayWrite(relayOffCmd_2[rV], 8, 50);
 
  // 2) 方向/停止（避免B和C同时开）
  if (dir == SUGAR_FWD) {            // 正转：B开C关
    relayWrite(relayOnCmd_2[rB], 8, 50);
    relayWrite(relayOffCmd_2[rC], 8, 50);
  } else if (dir == SUGAR_REV) {     // 反转：B关C开
    relayWrite(relayOffCmd_2[rB], 8, 50);
    relayWrite(relayOnCmd_2[rC], 8, 50);
  } else {                           // 停止：B关C关
    relayWrite(relayOffCmd_2[rB], 8, 50);
    relayWrite(relayOffCmd_2[rC], 8, 50);
  }
}

void handleSugar999(char chan) {
  bool isU = (chan == 'U' || chan =='V');  // U or V
  bool use24V = true;                 // 999 满管 -> 24V
  sugarSetState(isU, use24V, SUGAR_FWD);
}


// 解析并处理输入命令  //命令的样式 "A100B100_B050"这个的意思是给主机发送A100B100和给slaveMac1发送B050,"_B050"单独给slaveMac1发送命令，"A100B100"单独给主机发送命令
void processInputCommand(const String& input) {
  resetForNewCycle();     
  if (input.length() == 0) return; // 空命令直接返回5
  if (input.length() > 1 && input.charAt(0) == '*') {
    String s2cmd = input.substring(1);
    s2cmd.trim();
    if (s2cmd.length() > 0) {
      strncpy(myData.command, s2cmd.c_str(), sizeof(myData.command) - 1);
      myData.command[sizeof(myData.command) - 1] = '\0';
      esp_now_send(slaveMac2, (uint8_t*)&myData, sizeof(myData));
    }
    return;
  }

  // ===【插入】设备名查询：优先在这里拦截并立即回包 ===
  String q = input;
    q.trim();               // 去掉收尾空白/CR/LF
    String low = q;
    low.toLowerCase();      // 忽略大小写

    if (low == "device_name?") {
      // 回包一整行，供上位机按“行读取”立即收到
      Serial.print("device_name:");
      Serial.println(DEVICE_ID);    // DEVICE_ID 可是 String/const char*/宏字符串，println 都OK
      // 如PC端是走 Serial2(485)，把上面两行改为 Serial2.print/println
      return;                       // 直接返回，避免落入后续命令解析
    }

  int underscorePos = input.indexOf('_');
  // 情况1: 只有从机命令 (如 "_B050")
  if (underscorePos == 0) {
    String slaveCmd = input.substring(1); // 跳过开头的'_'
    if (slaveCmd.length() > 0) {
      // Serial.print("Processing slave-only command: ");
      // Serial.println(slaveCmd);
      processSlaveCommand(slaveCmd.c_str());
    }
    return;
  }
  // 情况2: 主机和从机组合命令 (如 "A100B100_B050")
  if (underscorePos > 0) {
    // 处理主机命令部分
    String masterCmd = input.substring(0, underscorePos);
    if (masterCmd.length() > 0) {
      // Serial.print("Processing master command: ");
      // Serial.println(masterCmd);
      processMasterCommand(masterCmd.c_str());
    }
    
  // 处理从机命令部分（改为：碎冰结束 + 拿起杯子(降重>50g) 后再下发给小料机）
    String slaveCmd = input.substring(underscorePos + 1);
    if (slaveCmd.length() > 0) {
      memset(deferredSlaveCmd, 0, sizeof(deferredSlaveCmd));
      strncpy(deferredSlaveCmd, slaveCmd.c_str(), sizeof(deferredSlaveCmd)-1);
      deferredSlaveCmd[sizeof(deferredSlaveCmd)-1] = '\0';
      deferSlaveUntilLift = true;

      // 不再使用“全停即发”的 pending 机制，避免提前触发
      hasPendingSlave = false;
      pendingSlaveCmd[0] = '\0';

      // 重置等待状态
      waitForCupLift = false;
      postIceWeightBaseline = 0;
      liftDropStart = 0;
    }
  }

  // 情况3: 只有主机命令 (如 "A100B100")
  if (underscorePos == -1) {
    Serial.print("Processing master-only command: ");
    Serial.println(input);
    processMasterCommand(input.c_str());
    return;
  }
}


void processMasterCommand(const char* command) {
  if (strcmp(command, "stop") == 0) {
    for (int i = 0; i < deviceCount; i++) {
      if (motorActive[i] == true){ 
        // Serial.print("Motor ");
        // Serial.print(i+1);
        Serial.println(" stop命令.");
        stopMotor(i);
        relayWrite(relayOffCmd_3[0], 8);
        delay(50);
        relayWrite(relayOffCmd_3[1], 8);   //关闭螺旋杆
        delay(50);
        relayWrite(relayOffCmd_3[2], 8);   //关闭螺旋杆
        delay(50);
        // 关闭冰机（碎冰电机）
        iceMotorStop();

        // PATCH: 同时关闭搅动电机（地址2第7/8位）
        stirMotorStop();
      } 
    }
    // for(int i=0;i<4;i++){
    //   SerialRelay.write(sugarOffCmd[i], 8);   //关闭糖通道
    //   delay(50);
    //   Serial.println("糖关闭了");
    // }
    sugarSetState(true,  true, SUGAR_OFF);   // U OFF
    sugarSetState(false, true, SUGAR_OFF);   // V OFF
    Serial.println("糖关闭了");

    ice_judge = 0;
    liquidsStageTriggered  = false;
    liquidsTargetSum       = 0;
    liquidsStageThresholdAbs = 0;

    commandReceived = false; // 重置标志
    isProcessingCommand = false;

    if (purgeDoneThisCycle){
    allMotorsInactive = true;}

    totalWeightCheckEnabled = false; // 停止时也禁用总重量检查
    return;
  }

  if (commandReceived || isProcessingCommand) {
    return;
  }
  commandReceived = true;
  isProcessingCommand = true;

    // —— 新增：百分比标志复位 ——
  totalSlowdownTriggered = false;
  totalStopTriggered     = false;

  isNegative = false;
  int startIndex = 0;
  totalTargetWeight = 0; // 重置总目标重量
  totalTargetWeight_pre = 0;
  // —— 两阶段总量控制：重置（新增） ——
  liquidsTargetSumAbs   = 0;
  liquidsCompSum        = 0;
  liquidsThresholdAbs   = 0;
  liquidsStageTriggered = false;
  liquidsTargetSum         = 0;


  // 判断是否全局负号
  if (command[0] == '-') {
    isNegative = true;
    startIndex = 1; // 跳过负号
  }

    // 检查命令是否包含 "A100"（决定是否跳过 A100 的值）H： 新添加 26-01-26
  bool containsA = (strstr(command, "A") != nullptr);

    // 计算总目标重量
  for (int i = startIndex; i < strlen(command); i += 4) {
    if (i + 3 < strlen(command)) {
      char cmdChar = command[i];
      int  weight  = atoi(&command[i + 1]);

      if ((cmdChar == 'L' || cmdChar == 'M' || cmdChar == 'N') && weight == 999) {
        continue;   // 直接跳过，既不置标志也不加总重。 H： 错误，不能跳过，历史遗留问题。但是不影响，因为 weight == 999不会发生
      }
      if (cmdChar >= 'C' && cmdChar <= 'Q' && weight > 0) hasPumpThisCycle = true;  // 目前没有任何用处
      if ((cmdChar == 'A' || cmdChar == 'B') && weight > 0) hasIceThisCycle  = true;
      
       // 包含A就跳过A，并发“start”给从机   H： 新添加 26-01-26
      if((containsA && cmdChar == 'A')) {

      continue; // 跳过 A（不计入任何总量）
      }

      // 第二次阈值用的总目标（= B + 所有水路）
      totalTargetWeight += weight;

      // —— 新增：第一次阈值仅统计“水路”（不含 A/B/总重）——
      int idx = cmdChar - sta_ch;                 // 'A' 基准
      if (idx >= 0 && idx < deviceCount && isLiquid(idx)) {   // ← 现在代表 F..K
          liquidsTargetSumAbs += weight;
          liquidsCompSum      += liquid_diff[idx];
      }
    }
  }

  // —— 新增：按通道惯性计算“先停水路”的绝对阈值 ——
  // 例如 CDE=350，target_diff={8,16,10} → 阈值 = 350 - 34 = 316
  liquidsThresholdAbs = liquidsTargetSumAbs - liquidsCompSum;
  if (liquidsThresholdAbs < 0) liquidsThresholdAbs = 0;  // 保险
  
  // 设置总重量检查
  if (totalTargetWeight > 0) {
    totalBaselineWeight = Weights[deviceCount-1]; // 假设Weights[0]是总重量传感器数据
    totalWeightCheckEnabled = true;
    purgeDoneThisCycle = false;
    purgeInProgress = false;
    for (uint8_t i = JAM_START; i <= JAM_END; ++i) {
      jamRanThisCycle[i] = false;
    }
    totalTargetWeight_pre = totalTargetWeight - totalTargetWeight_diff;
    // Serial.print("总重量目标设置为: ");
    // Serial.println(totalTargetWeight);
    // Serial.print("totalTargetWeight_pre: ");
    // Serial.println(totalTargetWeight_pre);
    // Serial.print("初始总重量: ");
    // Serial.println(totalBaselineWeight);
    totalSlowdownTriggered = false;
    totalStopTriggered     = false;
  }

 //命令需要是4位 "A50"需要"A050"才行
  for (int i = startIndex; i < strlen(command); i += 4) {
    char motor = command[i];
    int motorIndex = motor - sta_ch;
    if (motorIndex >= 0 && motorIndex < deviceCount) {
      targetWeights[motorIndex] = atoi(&command[i + 1]);
      if ((motor == 'U' || motor == 'V' ) && targetWeights[motorIndex] == 999) {
        handleSugar999(motor);             // 糖满管
        continue;                          // 跳过本通道的常规处理
      }
      motorActive[motorIndex] = true;
      if (motorIndex >= JAM_START && motorIndex <= JAM_END) {
        jamRanThisCycle[motorIndex] = true;
        Serial.printf("果酱通道索引: %d\n", motorIndex);
        Serial.printf("果酱通道: %d\n", jamRanThisCycle[motorIndex]);
      }
      allMotorsInactive = false;
      
    }
  }
  de_time = millis();
}

void processSlaveCommand(const char* cmd) {
  if (!cmd || !*cmd) return;
  if (allMotorsInactive) {
    strncpy(dataS1.command, cmd, sizeof(dataS1.command)-1);
    dataS1.command[sizeof(dataS1.command)-1] = '\0';
    esp_now_send(slaveMac1, (uint8_t*)&dataS1, sizeof(dataS1));
  } else {
    strncpy(pendingSlaveCmd, cmd, sizeof(pendingSlaveCmd)-1);
    pendingSlaveCmd[sizeof(pendingSlaveCmd)-1] = '\0';
    hasPendingSlave = true;
  }
}



// ===== Wi-Fi 连接（带超时）=====
void connectWiFi(uint32_t timeoutMs = 15000) {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - t0) < timeoutMs) {
    delay(300);
  }
}

// ===== 发送一次心跳（返回是否成功）=====
bool sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;

  // 简化：忽略证书校验（调试最快）。生产可改成 net.setCACert(root_ca)。
  net.setInsecure();

  if (!http.begin(net, PING_URL)) {
    http.end();
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + TOKEN);

  // 最小 JSON 体（插件只需要 id）
  String body = String("{\"id\":\"") + DEVICE_ID + "\"}";

  int code = http.POST(body);
  bool ok = (code == 200);
  // 可选：串口打印
  // Serial.printf("[PING] code=%d, ok=%d\n", code, ok);

  http.end();
  return ok;
}



void setup() {
  Serial.begin(9600);
  SerialRelay.begin(9600, SERIAL_8N1, RELAY_RX, RELAY_TX);
  SerialWeight.begin(115200, SERIAL_8N1, WEIGH_RX, WEIGH_TX);
  SerialWeight.setTimeout(20);
  relayQueue = xQueueCreate(64, sizeof(RelayCmd));
  if (relayQueue) {
    xTaskCreatePinnedToCore(relaySendTask, "RelayTx", 2048, nullptr, 3, nullptr, 0);
  }
  // connectWiFi();
  // sendHeartbeat();
  // lastPing = millis();
  lastrun=millis();
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  if (esp_now_init() != ESP_OK) {
    // Serial.println("Error initializing ESP-NOW, system will restart.");
    delay(1000);  // 延时1秒后重启，给出足够的时间显示错误信息
    esp_restart();
  }
  //添加1个从设备的 MAC 地址为 ESP-NOW 的对等设备，并打印主设备的 MAC 地址
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataRecv);
  addPeer(slaveMac1);
  addPeer(slaveMac2);
  // Serial.print("Master MAC: ");
  // Serial.println(WiFi.macAddress());

  
  pinMode(ENC1_A_PIN, INPUT_PULLUP);  // 接近开关信号（高电平有效），需外部上拉更稳
  pinMode(ENC2_A_PIN, INPUT_PULLUP);

  // PATCH: 搅动电机光电传感器（GPIO35 无内部上拉，需外部上拉/开漏等硬件保证）
  pinMode(STIR_ENC_PIN, INPUT_PULLUP);

  // 清洁主泵流量计：上拉输入（若为开漏/干接点，建议外部上拉更稳）
  pinMode(CLEAN_FLOW_PIN, INPUT_PULLUP);

// 碎冰接近开关（高电平有效） + 螺旋杆霍尔编码器（上升沿有效）
  attachInterrupt(digitalPinToInterrupt(ENC1_A_PIN), encoder1ISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC2_A_PIN), encoder2ISR, RISING);
  attachInterrupt(digitalPinToInterrupt(STIR_ENC_PIN), stirEncoderISR, RISING);
  attachInterrupt(digitalPinToInterrupt(CLEAN_FLOW_PIN), cleanFlowISR, RISING);

  // ===== PATCH: 三模块独立状态机绑定（含卡死检测/反转解卡/RPM打印） =====
  // pulsesPerRev 需要按你的实际编码器每转脉冲数修正：
  // - CRUSH/AUGER 若是单路霍尔/光电：常见 1/2/20 等
  // - STIR(GPIO35) 若是单个磁铁：通常 1
  fsmCrush.bind("CRUSH", &encoderTotal1, PULSES_PER_REV_CRUSH, iceMotorStop,  iceMotorForward,  iceMotorReverse);
  fsmCrush.enableStall = false; // 临时关闭卡死检测
  fsmAuger.bind("AUGER", &encoderTotal2, PULSES_PER_REV_AUGER, augerMotorStop, augerMotorForward, augerMotorReverse);
  fsmAuger.enableStall = false; // 临时关闭卡死检测
  fsmStir.bind ("STIR",  &stirEncoderTotal, PULSES_PER_REV_STIR,  stirMotorStop,  stirMotorForward,  stirMotorReverse);
  fsmStir.enableStall = false; // 临时关闭卡死检测

  // ===== 新版卡死检测：监测源初始化 =====
  stallCrush.tag = "ICE";
  stallCrush.total = &encoderTotal1;
  stallCrush.minPulses = 1;
  stallCrush.needWins  = 5;
  stallCrush.winMs     = 150;
  stallCrush.phaseMs   = 3000;
  stallCrush.maxCycles = 3;

  stallAuger.tag = "AUG";
  stallAuger.total = &encoderTotal2;
  stallAuger.minPulses = 1;
  stallAuger.needWins  = 5;
  stallAuger.winMs     = 150;
  stallAuger.phaseMs   = 3000;
  stallAuger.maxCycles = 3;

  stallStir.tag = "STIR";
  stallStir.total = &stirEncoderTotal;
  stallStir.minPulses = 1;
  stallStir.needWins  = 5;
  stallStir.winMs     = 150;
  stallStir.phaseMs   = 3000;
  stallStir.maxCycles = 3;


  xTaskCreatePinnedToCore(
    weightReadTask,     // 任务函数
    "WeightReadTask",   // 任务名
    4096,               // 栈大小
    NULL,               // 参数
    1,                  // 优先级
    &weightReadTaskHandle,              // 任务句柄
    0                   // 绑定到 Core 1
  );
  xTaskCreatePinnedToCore(
    Task_CheckTotalWeight, 
    "TotalCheck", 
    4096, 
    NULL, 
    1,
    NULL, 
    0
  ); // 栈 4KB，优先级 3，跑在 Core 0
  //  // 与 PN532_1.ino 一致：I2C 引脚 21/22
  // Wire.begin(PN532_SDA, PN532_SCL);

  // // 初始化 PN532
  // nfc.begin();
  // // 进入正常工作模式（SAMConfig 必须调用）
  // nfc.SAMConfig();
  Weights[11]=999;Weights[12]=999;Weights[13]=999;//？
}

static uint32_t idleJamLastTrigMs = 0;
static bool idleJamRunning = false;
static uint32_t idleJamStartMs = 0;
static bool idleWasActive = false;


void loop() {
  // checkMotorsMoving();
  // 新版卡死检测（两路接近+一路霍尔）
  // checkIceStallRecoveryNew(); // 临时关闭卡死脱困逻辑
  // if (millis() - lastPing >= PING_INTERVAL_MS) {
  //   lastPing = millis();
  //   sendHeartbeat();
  //   // 简单抖动
  //   delay(random(0, 2000));
  // }


  //空闲状态防堵操作
  // if(millis()-lastrun>=60000){
  //   if(allMotorsInactive&&Weights[1]>1000){
  //     lastrun=millis();
  //     SerialRelay.write(relayOffCmd_ICE_STIR_FWD,8);
  //     delay(50);
  //     SerialRelay.write(relayOnCmd_ICE_STIR_REV,8);
  //     delay(50);
  //     reverses_num++;   
  //     if(reverses_num>20){
  //         reverses_num=0;
  //         SerialRelay.write(relayOnCmd_3[0], 8);
  //         delay(50);
  //         SerialRelay.write(relayOffCmd_3[1], 8);
  //         delay(3000); //转动3S
  //         SerialRelay.write(relayOffCmd_3[0], 8);
  //         delay(50);
  //     }
  //   }
  // }
  const uint32_t now = millis();

  const bool hasIceIdle = (Weights[1] > 1000);
  const bool allInactiveNow = allMotorsInactive;
  if (allInactiveNow && idleWasActive) {
    // 刚进入空闲：重置计时，避免立即触发空闲反转
    idleJamLastTrigMs = now;
  }
  idleWasActive = !allInactiveNow;

  const uint32_t IDLE_REV_PERIOD_MS = 60000;
  const uint32_t IDLE_REV_RUN_MS = 3000;

  if (!idleJamRunning) {
    if (allMotorsInactive && hasIceIdle && (now - idleJamLastTrigMs >= IDLE_REV_PERIOD_MS)) {
      idleJamLastTrigMs = now;
      idleJamRunning = true;
      idleJamStartMs = now;

      // 开始反转（先关正转，再开反转）
      relayWrite(relayOffCmd_ICE_STIR_FWD, 8);
      delay(50);
      relayWrite(relayOnCmd_ICE_STIR_REV, 8);
      Serial.printf("[IDLE_JAM] start rev\n");
    }
  } else {
    if (now - idleJamStartMs >= IDLE_REV_RUN_MS) {
      // 3 秒到：停
      relayWrite(relayOffCmd_ICE_STIR_REV, 8);
      delay(50);
      relayWrite(relayOffCmd_ICE_STIR_FWD, 8);
      idleJamRunning = false;
      Serial.printf("[IDLE_JAM] stop rev\n");
    }
  }


  checkIceJude();
  checkLoops();
  // checkTotalWeight(); // 如需总重闭环可打开
  checkCupLiftTrigger();

  // 清洁主泵流量计：无流监测（仅清洁模式启用）
  if (cleanFlowMonitorEnabled) {
    uint32_t lastPulseMs;
    noInterrupts();
    lastPulseMs = cleanFlowLastPulseMs;
    interrupts();

    const uint32_t nowMs = millis();
    if (!cleanFlowPopupSent && lastPulseMs > 0 && (nowMs - lastPulseMs >= CLEAN_FLOW_LOST_MS)) {
      Serial.println("POPUP:清洁液余量告急，请添加清洁液");
      cleanFlowPopupSent = true;
    }
  }

  // 0) 先处理串口指令（更新 motorActive 等）
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // 直接在这里处理清洗命令
    if (input == "clean1_on") {
      Serial.println("clean1_on 命令收到，开启清洗1");
      relayWrite(CleanOnCmd[0], 8);
      delay(50);
      // 开启清洁主泵流量监测
      cleanFlowMonitorEnabled = true;
      cleanFlowPopupSent = false;
      noInterrupts();
      cleanFlowPulseCount = 0;
      cleanFlowLastPulseMs = millis();
      interrupts();
    }

    if (input == "clean2_on") {
      Serial.println("clean2_on 命令收到，开启清洗2");
      relayWrite(CleanOnCmd[1], 8);
      delay(50);
    }

    if (input == "clean1_off") {
      Serial.println("clean1_off 命令收到，关闭清洗1");
      relayWrite(CleanOffCmd[0], 8);
      delay(50);
      // 关闭清洁主泵流量监测并清状态
      cleanFlowMonitorEnabled = false;
      cleanFlowPopupSent = false;
      noInterrupts();
      cleanFlowPulseCount = 0;
      cleanFlowLastPulseMs = 0;
      interrupts();
    }

    if (input == "clean2_off") {
      Serial.println("clean2_off 命令收到，关闭清洗2");
      relayWrite(CleanOffCmd[1], 8);
      delay(50);
    }

    if (input.length() > 0) {
      // processMasterCommand(input.c_str());
      processInputCommand(input);
    }
  }

  

  // 2) 三个独立电机状态机 tick（卡死检测+反转解卡+RPM打印）
  //    FSM 只在 checkLoops() 放行(baseInit_judge=1)后才会运行
  // ===== FSM 已全量禁用（按要求） =====
  // 如需恢复，再启用下方 FSM 调度块。
  // const uint32_t nowMs = millis();
  // const bool workA = (motorActive[IDX_ICE]      && baseInit_judge[IDX_ICE]);
  // const bool workB = (motorActive[IDX_CRUSHED] && baseInit_judge[IDX_CRUSHED]);
  // const bool iceWorkActive = (workA || workB);
  // const bool hasIce = (Weights[IDX_CRUSHED] > 1000);
  // fsmAuger.requestDir(iceWorkActive ? DIR_FWD : DIR_STOP);
  // fsmCrush.requestDir(workB ? DIR_FWD : DIR_STOP);
  // if (iceWorkActive) {
  //   fsmStir.requestDir(workA ? DIR_FWD : DIR_STOP);
  // } else {
  //   fsmStir.requestDir(DIR_STOP);
  // }
  // fsmCrush.tick(nowMs);
  // fsmAuger.tick(nowMs);
  // fsmStir.tick(nowMs);

}

void checkLoops() {
  // Serial.printf("allMotorsInactive:%d\r\n",allMotorsInactive);

    // 检测碎冰刚刚停止 → 开始等待“拿杯”
  static bool _allmotorActivePrev = false;
  static uint32_t idleStateDbgLastMs = 0;
  const uint32_t nowMs = millis();
  bool _allmotorActiveNow = !allMotorsInactive;
  if (!_allmotorActiveNow && _allmotorActivePrev && deferSlaveUntilLift) {
    waitForCupLift = true;
    postIceWeightBaseline = Weights[deviceCount-1]; // 总重量通道
    liftDropStart = 0;
  }
  _allmotorActivePrev = _allmotorActiveNow;

  allMotorsInactive = true;
  for (int i = 0; i < deviceCount; i++) {
    if (isRecordingDischarge[i] && deviceAddresses[i] != 0x01) {
      // 出料完成1秒后记录最终重量
      if (millis() - dischargeCompleteTime[i] >= 1500) {
        afterDischargeWeights[i] = Weights[i];
        actualDischargeAmounts[i] = beforeDischargeWeights[i] - afterDischargeWeights[i];
        // Serial.print("出料前的重量: ");Serial.println(beforeDischargeWeights[i]);
        // Serial.print("出料后的重量: ");Serial.println(afterDischargeWeights[i]);
        // Serial.print("设备 ");
        // Serial.print(i+1);
        // Serial.print(" 出料量: ");
        // Serial.print(actualDischargeAmounts[i]);
        // Serial.println(" 克");
        isRecordingDischarge[i] = false;
      }
    }
    if (motorActive[i]) {
      if (isNegative) { //果酱反转
        if (isJamIdx(i)) {
          int j = (i - 2) * 2; // i=2→j=11, i=3→j=13, i=4→j=15
          if (!relayRunning[i]) { 
            relayWrite(relayOnCmd_4[j], 8, 50);  // 打开 1 号继电器
            relayWrite(relayOffCmd_4[j+1], 8, 50); // 关闭 2 号继电器
            // Serial.println("状态: 10 (打开 1 号继电器，关闭 2 号继电器)"); //反转
            motorRunDuration[i] = abs(targetWeights[i]) * 40;  // 转化为毫秒 100*40=4s
            // Serial.print("motorRunDuration:");
            // Serial.println(motorRunDuration[i]);
            motorStartTime[i] = millis();        // 记录开始时间
            relayRunning[i] = true;              // 启动标志
          }
          if (relayRunning[i] && millis() - motorStartTime[i] >= motorRunDuration[i]) { //反转执行时间为4s
            relayWrite(relayOffCmd_4[j], 8, 50); // 关闭 1 号继电器
            relayWrite(relayOffCmd_4[j+1], 8, 50); // 关闭 2 号继电器
            // Serial.println("状态: 00 (关闭 1 和 2 号继电器)");

            relayRunning[i] = false;
            motorActive[i] = false; // 停止该电机的运行状态
            targetWeights[i] = 0;
            time_check_to_stop[i] = 0;
            max_time_to_stop[i] = 0;
          }
          allMotorsInactive = false; // 有电机还在运行

        }else {
          targetWeights[i] = 0;
          motorActive[i] = false;
          baselineWeights[i] = 0;
          time_check_to_stop[i] = 0;
          max_time_to_stop[i] = 0;
          // Serial.println("该通道不是果酱");
          continue;
        }
      }else {   //正转
        // 正转
        if (!baseInit_judge[i]) {
          // 果酱
          if (isJamIdx(i)) {
            int j = (i - 2) * 2;
            // 真正开始前再设基线
            baseInit_judge[i] = true;
            time_check_to_stop[i] = millis();
            max_time_to_stop[i] = calcChannelMaxMs(i, targetWeights[i]);
            baselineWeights[i]      = Weights[i];
            beforeDischargeWeights[i] = Weights[i];

            relayWrite(relayOffCmd_4[j], 8, 50);
            relayWrite(relayOnCmd_4[j+1], 8, 50);
            // Serial.println("状态: 01 (关闭1开2) 果酱正转");
          }

          // 冰(方冰) —— A 通道：只开传送带/搅冰，不开碎冰电机
          // else if (i == IDX_ICE) {
          //   // 只有"所有水停 + 冰钥匙打开"才允许开
          //   if (allPumpsStopped()) {
          //     baseInit_judge[i] = true;
          //     time_check_to_stop[i] = millis();
          //     baselineWeights[i]      = Weights[i];
          //     beforeDischargeWeights[i] = Weights[i];
          //     lastrun=millis();

          //     Serial.println("🟢 方冰/传送带 已放行（FSM接管）");
          //     speed_judge = 1;
          //   } else {
          //     continue;
          //   }
          // }

          // 冰机
          else if (i == suib) {
            // 只有“所有水停 + 冰钥匙打开”才允许开
            if (ice_judge==1 && allPumpsStopped()) {
              // 真正开始前再设基线
              baseInit_judge[i] = true;
              time_check_to_stop[i] = millis();
              max_time_to_stop[i] = calcChannelMaxMs(i, targetWeights[i]);
              baselineWeights[i]      = Weights[i];
              beforeDischargeWeights[i] = Weights[i];
              lastrun=millis();

                // 开冰
                relayWrite(relayOffCmd_3[4], 8); 
                delay(50);
                relayWrite(relayOnCmd_3[3], 8); //碎冰模块
                delay(50);
                relayWrite(relayOffCmd_ICE_STIR_REV,8);//搅冰反转关闭
                delay(50);
                relayWrite(relayOnCmd_ICE_STIR_FWD,8);//搅冰正转开启
                delay(50);
                Serial.println("🟢 碎冰已开启");

                // 同步开传送带（只在冰启动时）
                relayWrite(relayOnCmd_3[0], 8);
                delay(50);
                relayWrite(relayOffCmd_3[1], 8);
                delay(50);
                // SerialRelay.write(relayOnCmd[1], 8); 
                // delay(50);
                Serial.println("🟢 传送带已开启");
                speed_judge = 1;
                ice_judge   = 0;   // 防止重复开

            } else {
              // 冰未被允许：啥也不做（也不要设基线），等下次循环再判断
              continue;
            }
          }

          // 水路
          else if (isLiquidIdx(i)) {
            // 真正开始前再设基线
            baseInit_judge[i] = true;
            time_check_to_stop[i] = millis();
            max_time_to_stop[i] = calcChannelMaxMs(i, targetWeights[i]);
            baselineWeights[i]      = Weights[i];
            beforeDischargeWeights[i] = Weights[i];

            relayWrite(relayOnCmd[i], 8);  // 只让水用这条“通用开启”
            delay(50);
            Serial.println("🟢 水路已开启");
          }

          else if (isSugarIdx(i) || isWaterIdx(i)) {
            baseInit_judge[i] = true;
            float grams = targetWeights[i];
            time_check_to_stop[i] = millis();
            max_time_to_stop[i] = calcChannelMaxMs(i, targetWeights[i]);

            // 目标出料时长（秒）：flow_rata[0]=U, [1]=V, [2]=水
            float sec;
            if (isSugarIdx(i)) sec = grams / flow_rata[i - SUG_START];
            else               sec = grams / flow_rata[2];

            if (sec < 0.05f) sec = 0.05f;
            if (sec > 600.0f) sec = 600.0f;

            // 1) 打开执行器
            if (isSugarIdx(i)) {
              bool isU = (i == SUG_START);
              bool use24V = false;                 // 正常出料默认5V
              sugarSetState(isU, use24V, SUGAR_FWD);
              Serial.println("🟢 糖泵开启成功");
            } else {
              // 水泵：如 relayOnCmd[IDX_WATER] 已配置则会生效
              relayWrite(relayOnCmd[i], 8);
              delay(50);
              Serial.println("🟢 水泵开启成功");
            }

            // 2) 记录计时（由 weightReadTask 统一按时间关断）
            sugarStartMs[i] = millis();
            sugarStopMs[i]  = (uint32_t)(sec * 1000.0f);
            sugarActive[i]  = true;
            motorActive[i]  = true;
          }


          // 其它（比如总重、占位等）：不做启动
          else {
            continue;
          }
        }



        allMotorsInactive = false;
        int currentWeight = Weights[i];
        
        if (currentWeight != INVALID_WEIGHT) {
          // **检查重量是否达到目标**
          weightDiff[i] = baselineWeights[i] - currentWeight;
     
          if (deviceAddresses[i] == 0x01) { 
            num = 1;           //冰 
          }else if (isJamIdx(i)) {
            num = 2;          //果酱
          }else { 
            num = 3;           //水
          }
          // Serial.print("num:"); Serial.println(num);
          if (num == 1) {
            
            
          }
          else if (num == 2) { //果酱
            if (weightDiff[i] >= (targetWeights[i] - target_diff[i])) {
              Serial.print("Motor ");
              Serial.print(i);
              Serial.print("baselineWeights:");
              Serial.print( baselineWeights[i]);
              Serial.print("currentWeight:");
              Serial.print( currentWeight);
              Serial.print("weightDiff:");
              Serial.print(weightDiff[i]);
              Serial.print(" target_diff:");
              Serial.print(target_diff[i]);
              Serial.println(" 果酱停止了。。。。。。。。。。。。。。。。。。。。。。。。。。。");
              stopMotor(i);
            }
          }
          else {  // 水 —— 单点检测，达到本路预定重量就停止
            // weightDiff[i] = baselineWeights[i] - currentWeight;
            // if (weightDiff[i] >= targetWeights[i]) {
           if (weightDiff[i] >= (targetWeights[i] - target_diff[i]) ) {
              // Serial.print("水路达到设定值，停止。通道=");
              // Serial.print(Weights[i]);
              // Serial.print(" 实际差值=");
              // Serial.print(beforeDischargeWeights[i]);
              // Serial.print(" 目标=");
              // Serial.println(targetWeights[i]);

              stopMotor(i);   // 停止当前这一路液体电机
            }
          }
        } 
      }
    }
    continue;
  }
  // if (ice_judge == 0 && allLiquidsStopped()) {
  // // ice_judge = 1;  // 所有水路停止 → 放行冰机
  // }

  if (allMotorsInactive) {
    if (hasPendingSlave && pendingSlaveCmd[0] != '\0'&& !deferSlaveUntilLift) {
      strncpy(dataS1.command, pendingSlaveCmd, sizeof(dataS1.command)-1);
      dataS1.command[sizeof(dataS1.command)-1] = '\0';
      esp_now_send(slaveMac1, (uint8_t*)&dataS1, sizeof(dataS1));
      pendingSlaveCmd[0] = '\0';
      hasPendingSlave = false;
    }
    if (totalStopTriggered || (!hasIceThisCycle && purgeDoneThisCycle)) {
      commandReceived = false;
      isProcessingCommand = false;
      totalWeightCheckEnabled = false;
    }
  }
  else {
    for (int i=0; i<deviceCount; i++) {
      last_time_check_to_stop[i] = millis();
      const uint32_t limit_ms = (max_time_to_stop[i] > 0) ? max_time_to_stop[i] : (uint32_t)timer;
      if (time_check_to_stop[i] != 0 && (last_time_check_to_stop[i] - time_check_to_stop[i] >= limit_ms)) {
        if (motorActive[i] == true) {
          // Serial.println("自动停止电机");
          stopMotor(i);
          relayWrite(relayOffCmd_3[0], 8);
          delay(50);
          relayWrite(relayOffCmd_3[1], 8);
          delay(50);
          relayWrite(relayOffCmd_3[2], 8);
          delay(50);
          relayWrite(relayOffCmd_3[3], 8);
          delay(50);
          relayWrite(relayOffCmd_3[4], 8);
          delay(50);
          relayWrite(relayOffCmd_ICE_STIR_FWD,8);
          delay(50);
          relayWrite(relayOffCmd_ICE_STIR_REV,8);
          delay(50);
          time_check_to_stop[i]=0;
          max_time_to_stop[i]=0;
        }
      }
    }
  }
}


// ---------- 一次会话：开始 / 多次读 / 结束 ----------

// 1) 开始会话：检测并选中卡片（只在本轮第一步调用）
//    “每次放卡只读一次”：同一张卡未移开前返回 false
bool beginCard() {
  if (!nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLen, 50)) {
    // 没有卡：标记无卡；若上一张卡已读过且已移开，释放门控
    hasCard = false;
    if (lastUidLen > 0 && hasReadCurrentCard) {
      lastUidLen = 0;
      hasReadCurrentCard = false;
    }
    return false;
  }

  // 检测到卡
  if (!hasCard) {
    // 新进入天线区的卡
    hasCard = true;
    memcpy(lastUid, uid, uidLen);
    lastUidLen = uidLen;
    hasReadCurrentCard = false;
  }

  // 若同一张卡且已读过，则不再触发
  if (hasReadCurrentCard &&
      uidLen == lastUidLen &&
      memcmp(uid, lastUid, uidLen) == 0) {
    return false;
  }

  return true; // 允许读取
}

// 2) 在“已选中卡片”的前提下，读取某块的前 n 字节（本轮可多次调用）
void readBlockBytesOnce(int block, int count) {
  num1++;
  if (count < 1)  count = 1;
  if (count > 16) count = 16;

  // —— 按 MIFARE Classic 的块/扇区鉴权方式——
  int trailerBlock = (block / 4) * 4 + 3;  // 本扇区的 trailer 块

  // KeyA 鉴权（keyNumber: 0 = KeyA, 1 = KeyB）
  if (!nfc.mifareclassic_AuthenticateBlock(uid, uidLen, trailerBlock, 0, keyA)) {
    return; // 鉴权失败：安静返回
  }

  // 读取目标块（16 字节）
  uint8_t data[16];
  if (!nfc.mifareclassic_ReadDataBlock(block, data)) {
    return; // 读取失败：安静返回
  }

  // —— 仅输出：num: + 可打印字符（非可打印用'.'代替）——
  Serial.print(num1);
  Serial.print(":");
  for (int i = 0; i < count; i++) {
    char c = (data[i] >= 32 && data[i] <= 126) ? (char)data[i] : '.';
    Serial.print(c);
  }
  Serial.println();
}

// 3) 结束会话：统一收尾（只在本轮最后一步调用）
//    标记“本张卡已读过一次”，无需调用 inRelease()
void endCard() {
  hasReadCurrentCard = true;
}
