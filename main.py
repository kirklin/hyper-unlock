import subprocess
import time
import json
import requests
import base64
import hmac
import adbutils 
import os.path as op
import platform
from typing import Optional, Dict, Any

# 定义常量
COLORS = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'end': '\033[0m'
}

# API配置
API_CONFIG = {
    'global': "https://unlock.update.intl.miui.com/v1/",
    'china': "https://unlock.update.miui.com/v1/"
}

# 加密相关常量
ENCRYPTION_CONFIG = {
    'sign_key': "10f29ff413c89c8de02349cb3eb9a5f510f29ff413c89c8de02349cb3eb9a5f5",
    'data_pass': "20nr1aobv2xi8ax4",
    'data_iv': "0102030405060708"
}

# 错误消息
ERROR_MESSAGES = {
    401: ("账号认证失败，请重新登录。", "Authentication failed, please login again."),
    20086: ("设备证书已过期，请重新获取。", "Device certificate expired, please obtain a new one."),
    30001: ("解锁失败：该账号已被小米强制验证。", "Unlock failed: Account requires Xiaomi verification."),
    86015: ("解锁操作失败，请稍后重试。", "Unlock operation failed, please try again later.")
}

# 检查必要的加密库
try:
    from Crypto.Cipher import AES
except ImportError:
    print(f"{COLORS['red']}错误：缺少必要的加密库。请运行以下命令：")
    print("Error: Missing required encryption library. Please run:")
    print(f"{COLORS['yellow']}pip uninstall pycrypto pycryptodome crypto")
    print("pip install pycryptodome>=3.19.0{COLORS['end']}")
    exit(1)
import hashlib

# 配置
use_global = False
api = API_CONFIG['global'] if use_global else API_CONFIG['china']
adb_bin = 'adb.exe' if platform.system() == 'Windows' else 'adb'
version = "1.0"

def logf(message: str, color: str = 'green', symbol: str = '*', show_en: bool = True) -> None:
    """
    统一的日志输出函数
    
    Args:
        message: 要显示的消息
        color: 颜色选择 ('red', 'green', 'yellow', 'blue')
        symbol: 消息前的符号
        show_en: 是否显示英文翻译
    """
    color_code = COLORS.get(color, COLORS['green'])
    print(f"{color_code}{symbol} {message}{COLORS['end']}")

def decrypt_data(data: str) -> Optional[str]:
    """
    解密数据
    
    Args:
        data: 需要解密的base64编码数据
    
    Returns:
        解密后的字符串，失败返回None
    """
    if not data:
        logf("错误：没有数据需要解密 | Error: No data to decrypt", "red", "!")
        return None
    try:
        decoded_data = base64.b64decode(data)
        cipher = AES.new(
            ENCRYPTION_CONFIG['data_pass'].encode('utf-8'),
            AES.MODE_CBC,
            ENCRYPTION_CONFIG['data_iv'].encode('utf-8')
        )
        decrypted = cipher.decrypt(decoded_data)
        result = decrypted.decode('utf-8').rstrip()
        if not result:
            logf("错误：解密结果为空 | Error: Decryption result is empty", "red", "!")
            return None
        return result
    except Exception as e:
        logf(f"解密错误 | Decryption error: {e}", "red", "!")
        return None

def sign_data(data: str) -> Optional[str]:
    """
    对数据进行签名
    
    Args:
        data: 需要签名的数据
    
    Returns:
        签名后的字符串，失败返回None
    """
    try:
        message = f"POST\n/v1/unlock/applyBind\ndata={data}&sid=miui_sec_android"
        signature = hmac.new(
            ENCRYPTION_CONFIG['sign_key'].encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha1
        ).hexdigest()
        return signature.lower()
    except Exception as e:
        logf(f"签名错误 | Signing error: {e}", "red", "!")
        return None

def post_api(endpoint: str, data: Dict[str, Any], headers: Dict[str, str], ignore: bool = False) -> Optional[Dict]:
    """
    发送POST请求到API
    
    Args:
        endpoint: API端点
        data: 请求数据
        headers: 请求头
        ignore: 是否忽略错误
    
    Returns:
        响应JSON数据，失败返回None
    """
    try:
        url = f"{api}{endpoint}"
        response = requests.post(url, data=data, headers=headers)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        logf(f"API请求错误 | API request error: {e}", "red", "!")
        return None

def main():
    """主程序入口"""
    # 显示欢迎信息
    logf("="*40)
    logf(f"Xiaomi HyperOS BootLoader Bypass Tool v{version}")
    logf("By Kirk")
    logf("="*40)
    logf("请确保已安装旧版设置 | Please ensure old version settings are installed")
    logf("="*40)

    # 连接设备
    try:
        adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
        device = adb.device()
    except Exception as e:
        logf(f"无法连接到设备 | Cannot connect to device: {e}", "red", "!")
        exit(1)

    logf("正在连接设备... | Connecting to device...")

    try:
        # 清理日志并准备设备
        device.shell("logcat -c")
        device.shell("svc data enable")
        app_info = device.app_current()
        focus = app_info.activity
        
        if focus != "com.android.settings":
            if focus != "NotificationShade":
                device.shell("am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS")
        else:
            if focus != "com.android.settings.bootloader.BootloaderStatusActivity":
                device.shell("am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS")
    except Exception as e:
        logf(f"设备操作错误 | Device operation error: {e}", "red", "!")
        exit(1)

    time.sleep(5)
    logf("请绑定小米账号 | Please bind your Mi Account", "yellow")

    # 捕获日志
    args = headers = None
    try:
        with subprocess.Popen(
            f"{adb_bin} logcat *:S CloudDeviceStatus:V",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as process:
            for output in process.stdout:
                output = output.decode('utf-8').strip()
                
                if "CloudDeviceStatus: args:" in output:
                    args = output.split("args:")[1].strip()
                    device.shell("svc data disable")
                
                if "CloudDeviceStatus: headers:" in output:
                    headers = output.split("headers:")[1].strip()
                    logf("已捕获请求 | Request captured")
                    process.kill()
                    break
    except Exception as e:
        logf(f"日志捕获错误 | Log capture error: {e}", "red", "!")
        exit(1)

    logf("正在处理参数... | Processing parameters...")
    if not args:
        logf("错误：未能获取请求参数 | Error: Failed to get request parameters", "red", "!")
        exit(1)

    # 处理数据
    data = decrypt_data(args)
    if not data:
        logf("错误：解密参数失败 | Error: Failed to decrypt parameters", "red", "!")
        exit(1)

    try:
        data = json.loads(data)
        data["rom_version"] = data["rom_version"].replace("V816", "V14")
        data = json.dumps(data)
    except json.JSONDecodeError as e:
        logf(f"错误：JSON解析失败 | JSON parsing error: {e}", "red", "!")
        exit(1)

    # 生成签名
    sign = sign_data(data)
    if not sign:
        logf("错误：生成签名失败 | Error: Failed to generate signature", "red", "!")
        exit(1)

    # 处理headers
    headers_decrypted = decrypt_data(headers)
    if not headers_decrypted:
        logf("错误：解密headers失败 | Error: Failed to decrypt headers", "red", "!")
        exit(1)

    cookies = None
    if "Cookie=[" in headers_decrypted:
        cookies = headers_decrypted.split("Cookie=[")[1].split("]")[0].strip()

    if not cookies:
        logf("错误：未能获取cookies | Error: Failed to get cookies", "red", "!")
        exit(1)

    # 发送解锁请求
    logf("正在发送解锁请求... | Sending unlock request...")
    res = post_api("unlock/applyBind", {
        "data": data,
        "sid": "miui_sec_android",
        "sign": sign
    }, {
        "Cookie": cookies,
        "Content-Type": "application/x-www-form-urlencoded"
    }, True)

    device.shell("svc data enable")

    # 处理响应
    if not res:
        logf("错误：网络连接问题 | Error: Network connection issue", "red", "!")
    else:
        code = res.get("code")
        if code == 0:
            logf(f"账号绑定成功 | Account bound successfully: {res['data']['userId']}", "green")
            logf("解锁过程完成，请使用解锁工具继续 | Unlock process completed, please proceed with unlock tool", "green")
        else:
            error_msg = ERROR_MESSAGES.get(code, (f"未知错误 | Unknown error: {res.get('descEN')}", f"Unknown error: {res.get('descEN')}"))
            logf(f"{error_msg[0]} ({code})", "yellow")
            logf(f"{error_msg[1]} ({code})", "yellow")

if __name__ == "__main__":
    main()
