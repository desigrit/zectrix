// NOTE4C only. SSD2683 sequence follows LazyYoun's MIT-licensed four-color driver.
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <SPI.h>
#include <driver/gpio.h>
#include <driver/rtc_io.h>
#include <esp_sleep.h>
#include <mbedtls/sha256.h>
#include <sys/time.h>
#include "font6x12.h"

constexpr int POWER=17, EPD_POWER=6, DC=10, CS=11, EPD_SCK=12, EPD_MOSI=13, RST=9, EPD_BUSY=8, BOOT=0;
constexpr size_t FRAME_BYTES=30000;
uint8_t frame[FRAME_BYTES];
Preferences prefs;
SPIClass epd(FSPI);
String ssid, wifiPassword, controller, deviceKey, displayedDigest;

uint32_t secondsToNextWake() {
  time_t now=time(nullptr);
  // A power loss can invalidate the RTC. Never invent a time or wake overnight.
  if(now<1735689600)return 0;
  String schedule=prefs.getString("wakes","");
  int begin=0;
  while(begin<(int)schedule.length()) {
    int comma=schedule.indexOf(',',begin);if(comma<0)comma=schedule.length();
    unsigned long slot=strtoul(schedule.substring(begin,comma).c_str(),nullptr,10);
    if(slot>(unsigned long)now)return (uint32_t)(slot-now);
    begin=comma+1;
  }
  return 0;
}

bool acceptSchedule(const String &epoch,const String &schedule) {
  unsigned long stamp=strtoul(epoch.c_str(),nullptr,10);
  if(stamp<1735689600 || schedule.length()<10 || schedule.length()>512)return false;
  for(size_t i=0;i<schedule.length();i++)if(!isDigit(schedule[i])&&schedule[i]!=',')return false;
  struct timeval now={(time_t)stamp,0};settimeofday(&now,nullptr);
  prefs.putString("wakes",schedule);
  return secondsToNextWake()>0;
}

void powerPin(int pin, int value) {
  gpio_hold_dis((gpio_num_t)pin);
  pinMode(pin, OUTPUT);
  digitalWrite(pin, value);
  gpio_hold_en((gpio_num_t)pin);
}

void sendCommand(uint8_t value) {
  digitalWrite(DC,LOW); digitalWrite(CS,LOW); epd.transfer(value); digitalWrite(CS,HIGH);
}
void sendData(uint8_t value) {
  digitalWrite(DC,HIGH); digitalWrite(CS,LOW); epd.transfer(value); digitalWrite(CS,HIGH);
}
bool waitReady() {
  uint32_t started=millis();
  while(digitalRead(EPD_BUSY)==LOW) {
    if(millis()-started>120000) { Serial.println("Display busy timeout; frame not confirmed."); return false; }
    delay(50);
  }
  return true;
}

bool showFrame() {
  powerPin(EPD_POWER,1); delay(10);
  pinMode(DC,OUTPUT); pinMode(CS,OUTPUT); pinMode(RST,OUTPUT); pinMode(EPD_BUSY,INPUT);
  digitalWrite(CS,HIGH);
  epd.begin(EPD_SCK,-1,EPD_MOSI,CS);
  epd.beginTransaction(SPISettings(4000000,MSBFIRST,SPI_MODE0));
  digitalWrite(RST,HIGH); delay(10); digitalWrite(RST,LOW); delay(20); digitalWrite(RST,HIGH); delay(10);
  bool ok=waitReady();
  if(ok) { sendCommand(0xE9); sendData(0x01); sendCommand(0x10); ok=waitReady(); }
  if(ok) {
    for(int y=0;y<300;y++) {
      digitalWrite(DC,HIGH); digitalWrite(CS,LOW);
      epd.writeBytes(frame+y*100,100); digitalWrite(CS,HIGH);
      if(y%16==15) delay(1);
    }
    sendCommand(0x04); ok=waitReady(); delay(10);
  }
  if(ok) { sendCommand(0x12); sendData(0x00); delay(10); ok=waitReady(); }
  if(ok) { sendCommand(0x02); sendData(0x00); ok=waitReady(); delay(20); }
  if(ok) { sendCommand(0x07); sendData(0xA5); }
  epd.endTransaction(); epd.end(); powerPin(EPD_POWER,0);
  return ok;
}

void pixel(int x,int y,uint8_t color) {
  if(x<0||x>=400||y<0||y>=300) return;
  size_t p=y*400+x; uint8_t shift=6-((p&3)*2);
  frame[p>>2]=(frame[p>>2]&~(3<<shift))|(color<<shift);
}
void textAt(int x,int y,const String &text,uint8_t color=0,int scale=1) {
  for(size_t i=0;i<text.length();i++) {
    unsigned char c=text[i]; if(c<32||c>126)c='?';
    for(int row=0;row<12;row++)for(int col=0;col<6;col++) {
      if(FONT6X12[c-32][row]&(1<<(7-col)))
        for(int a=0;a<scale;a++)for(int b=0;b<scale;b++)pixel(x+col*scale+a,y+row*scale+b,color);
    }
    x+=6*scale;
  }
}

void sleepFor(uint32_t seconds) {
  WiFi.disconnect(true); WiFi.mode(WIFI_OFF);
  powerPin(EPD_POWER,0); powerPin(42,0); powerPin(46,0); powerPin(21,1); powerPin(3,1);
  powerPin(POWER,1);
  pinMode(BOOT,INPUT_PULLUP);
  // A held BOOT button must not cause a rapid wake loop.
  for(int i=0;i<100 && digitalRead(BOOT)==LOW;i++)delay(20);
  if(digitalRead(BOOT)==HIGH) {
    rtc_gpio_pullup_en(GPIO_NUM_0); rtc_gpio_pulldown_dis(GPIO_NUM_0);
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0,0);
  }
  if(seconds>0)esp_sleep_enable_timer_wakeup((uint64_t)seconds*1000000ULL);
  gpio_deep_sleep_hold_en();
  Serial.println("Sleeping. Front button wakes for a manual refresh."); Serial.flush();
  esp_deep_sleep_start();
}

bool validController(const String &url) {
  if(!url.startsWith("http://"))return false;
  String host=url.substring(7); int colon=host.indexOf(':');
  if(colon>=0) {
    String port=host.substring(colon+1);
    if(port.length()==0||port.toInt()<1||port.toInt()>65535)return false;
    for(size_t i=0;i<port.length();i++)if(!isDigit(port[i]))return false;
    host=host.substring(0,colon);
  }
  IPAddress ip; if(!ip.fromString(host))return false;
  return ip[0]==10 || (ip[0]==192&&ip[1]==168) || (ip[0]==172&&ip[1]>=16&&ip[1]<=31);
}

void provision() {
  uint32_t random=esp_random();
  String suffix=String((uint32_t)(ESP.getEfuseMac()&0xffff),HEX); suffix.toUpperCase();
  String apName="Note-Setup-"+suffix;
  String apPassword="note-"+String(random,HEX);
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(IPAddress(192,168,4,1),IPAddress(192,168,4,1),IPAddress(255,255,255,0));
  WiFi.softAP(apName.c_str(),apPassword.c_str());
  DNSServer dns;dns.start(53,"*",WiFi.softAPIP());
  Serial.println("Setup Wi-Fi active at http://192.168.4.1");
  memset(frame,0x55,sizeof(frame));
  textAt(20,20,"SET UP YOUR NOTE",3,2);
  textAt(20,64,"1. On your phone, join this Wi-Fi:");
  textAt(20,86,apName,0,2);
  textAt(20,120,"Password: "+apPassword);
  textAt(20,154,"2. Open http://192.168.4.1");
  textAt(20,181,"3. Enter home Wi-Fi and Pi pairing details.");
  textAt(20,217,"Use a 2.4 GHz home network.");
  textAt(20,244,"Setup pauses after 30 minutes idle.");
  showFrame();
  WebServer web(80); bool saved=false;
  uint32_t lastActivity=millis();
  web.on("/",HTTP_GET,[&](){
    lastActivity=millis();
    String html=R"HTML(<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Set up Note</title><style>body{font:16px/1.5 system-ui;max-width:420px;margin:32px auto;padding:20px;background:#f5f3ed;color:#292b28}h1{font-size:26px}label{display:block;margin:18px 0 4px}input,button{box-sizing:border-box;width:100%;padding:12px;font:inherit;border:1px solid #999;border-radius:5px}button{margin-top:24px;background:#871f2b;color:white;border:0}small{display:block;color:#666;margin-top:8px}</style><h1>Set up your Note</h1><p>Connect to your 2.4 GHz home Wi-Fi and the Raspberry Pi controller.</p><form method="post" action="/save"><label>Wi-Fi name<input name="ssid" maxlength="32" required></label><label>Wi-Fi password<input name="password" type="password" maxlength="63"></label><label>Controller address<input name="controller" placeholder="http://192.168.1.100:29174" required></label><label>Device key<input name="key" type="password" required maxlength="128"></label><small>Find the address and key under Show pairing details in your controller.</small><button>Save and connect</button></form><script>setInterval(()=>fetch("/setup/ping",{cache:"no-store"}).catch(()=>{}),20000);</script></html>)HTML";
    web.sendHeader("Cache-Control","no-store"); web.send(200,"text/html",html);
  });
  web.on("/save",HTTP_POST,[&](){
    lastActivity=millis();
    String enteredSsid=web.arg("ssid"),enteredPassword=web.arg("password"),enteredController=web.arg("controller"),enteredKey=web.arg("key");
    enteredController.trim(); while(enteredController.endsWith("/"))enteredController.remove(enteredController.length()-1);
    if(enteredSsid.isEmpty()||enteredSsid.length()>32||enteredPassword.length()>63||!validController(enteredController)||enteredKey.length()<32||enteredKey.length()>128) {
      web.send(400,"text/plain","Check the Wi-Fi name, local controller address and full device key, then go back and try again.");return;
    }
    prefs.putString("ssid",enteredSsid);prefs.putString("wifi",enteredPassword);prefs.putString("controller",enteredController);prefs.putString("key",enteredKey);
    prefs.remove("digest");
    web.send(200,"text/html","<h1>Settings saved</h1><p>Your Note is connecting. Rejoin your home Wi-Fi. Allow a minute for the display to update.</p>");
    saved=true;
  });
  web.on("/setup/ping",HTTP_GET,[&](){lastActivity=millis();web.sendHeader("Cache-Control","no-store");web.send(204,"text/plain","");});
  web.onNotFound([&](){lastActivity=millis();web.sendHeader("Location","http://192.168.4.1/");web.send(302,"text/plain","Open the Note setup page.");});
  web.begin();Serial.println("Setup HTTP server ready.");
  while(!saved && millis()-lastActivity<1800000UL){dns.processNextRequest();web.handleClient();delay(5);}
  delay(1500);web.stop();dns.stop();
  if(saved){Serial.println("Wi-Fi and pairing settings saved. Restarting.");ESP.restart();}
  memset(frame,0x55,sizeof(frame));
  textAt(20,40,"SETUP PAUSED",3,2);
  textAt(20,98,"Press the front button to reopen setup.");
  textAt(20,128,"Then join Note-Setup with its new password.");
  showFrame();
  sleepFor(0);
}

String digestFrame() {
  uint8_t result[32];mbedtls_sha256_ret(frame,FRAME_BYTES,result,0);
  char hex[65];for(int i=0;i<32;i++)snprintf(hex+i*2,3,"%02x",result[i]);hex[64]=0;
  return String(hex);
}

bool fetchFrame(uint32_t &sleepSeconds) {
  WiFiClient client;HTTPClient http;
  http.setTimeout(60000);http.setConnectTimeout(10000);
  if(!http.begin(client,controller+"/device/frame"))return false;
  const char *names[]={"ETag","X-Sleep-Seconds","X-Server-Time","X-Wake-Schedule"};http.collectHeaders(names,4);
  http.addHeader("Authorization","Bearer "+deviceKey);
  http.addHeader("X-Wake-Reason",esp_sleep_get_wakeup_cause()==ESP_SLEEP_WAKEUP_TIMER?"timer":"manual");
  if(displayedDigest.length()==64)http.addHeader("If-None-Match","\""+displayedDigest+"\"");
  int status=http.GET();
  if(status==200||status==304)acceptSchedule(http.header("X-Server-Time"),http.header("X-Wake-Schedule"));
  String expected=http.header("ETag");expected.replace("\"","");
  bool ok=false;
  if(status==304 && displayedDigest.length()==64)ok=true;
  else if(status==200 && http.getSize()==FRAME_BYTES) {
    WiFiClient *stream=http.getStreamPtr();stream->setTimeout(30000);
    size_t read=stream->readBytes(frame,FRAME_BYTES);
    if(read==FRAME_BYTES && expected.length()==64 && digestFrame()==expected) {
      http.end();
      if(showFrame()) {displayedDigest=expected;prefs.putString("digest",displayedDigest);ok=true;}
    }
  }
  http.end();
  if(ok) {
    HTTPClient ack;WiFiClient ackClient;
    ack.setTimeout(10000);
    if(ack.begin(ackClient,controller+"/device/ack")) {
      ack.addHeader("Authorization","Bearer "+deviceKey);ack.addHeader("Content-Type","application/json");
      ack.POST("{\"digest\":\""+displayedDigest+"\"}");ack.end();
    }
  }
  sleepSeconds=secondsToNextWake();
  return ok;
}

void setup() {
  powerPin(POWER,1);powerPin(EPD_POWER,0);powerPin(42,0);powerPin(46,0);powerPin(21,1);powerPin(3,1);
  gpio_deep_sleep_hold_dis();
  pinMode(BOOT,INPUT_PULLUP);Serial.begin(115200);
  prefs.begin("note-calendar",false);
  ssid=prefs.getString("ssid","");wifiPassword=prefs.getString("wifi","");controller=prefs.getString("controller","");deviceKey=prefs.getString("key","");displayedDigest=prefs.getString("digest","");
  uint32_t held=millis();while(digitalRead(BOOT)==LOW && millis()-held<3000)delay(20);
  bool setupRequested=digitalRead(BOOT)==LOW && millis()-held>=3000;
  if(ssid.isEmpty()||deviceKey.isEmpty()||setupRequested)provision();
  WiFi.mode(WIFI_STA);WiFi.begin(ssid.c_str(),wifiPassword.c_str());
  uint32_t started=millis();while(WiFi.status()!=WL_CONNECTED && millis()-started<30000)delay(250);
  if(WiFi.status()!=WL_CONNECTED){Serial.println("Wi-Fi unavailable; saved display retained.");if(displayedDigest.isEmpty())provision();sleepFor(secondsToNextWake());}
  uint32_t seconds=secondsToNextWake();
  if(!fetchFrame(seconds))Serial.println("Frame update was not confirmed; saved display retained.");
  sleepFor(seconds);
}
void loop() {}
