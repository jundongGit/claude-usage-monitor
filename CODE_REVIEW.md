# 代码审查报告

## 🔴 严重安全问题

### 1. **敏感数据明文存储**
**位置**: `save_config()` - 第59-66行
**问题**: Cookie 以明文形式存储在 `~/.claude_usage_config.json`
**风险等级**: 🔴 高
**影响**:
- 任何有权限访问用户目录的程序都能读取 Cookie
- 恶意软件可以窃取 Claude 账户访问权限

**建议修复**:
```python
# 使用 macOS Keychain 存储敏感信息
import keyring
keyring.set_password("claude-usage-monitor", "cookie", self.cookie)
```

### 2. **配置文件权限不当**
**位置**: `save_config()` - 第65-66行
**问题**: 创建的配置文件使用默认权限 (644)，其他用户可读
**风险等级**: 🔴 高
**建议**: 创建文件后立即设置权限为 600

```python
with open(self.config_file, 'w') as f:
    json.dump(config, f)
os.chmod(self.config_file, 0o600)  # 仅所有者可读写
```

---

## 🟡 中等安全问题

### 3. **JSON 解析错误处理不足**
**位置**: `load_config()` - 第50-57行
**问题**: 文件损坏时会导致程序崩溃
```python
try:
    config = json.load(f)
except json.JSONDecodeError as e:
    print(f"配置文件损坏: {e}")
    # 备份损坏文件并重置配置
```

### 4. **输入验证缺失**
**位置**: `set_cookie()` - 第134-147行
**问题**: 用户输入的 Cookie 和 org_id 没有基本验证
**建议**:
```python
# 验证 org_id 格式（UUID）
import re
uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if not re.match(uuid_pattern, org_id):
    rumps.alert("错误", "组织 ID 格式不正确")
    return
```

### 5. **日志泄露敏感信息**
**位置**: 第198行
**问题**: `print(f"API 返回数据: {json.dumps(data...)})` 在生产环境会记录到日志
**建议**: 添加开关或仅在调试模式输出

---

## 🟢 性能和功能优化

### 6. **重复通知问题** ⚠️
**位置**: 第270-275行
**问题**: 每次刷新都可能发送通知，用户会被打扰
**建议**: 添加通知防重复机制
```python
def __init__(self):
    self.last_notification_time = {}

def should_notify(self, key, threshold=300):  # 5分钟内不重复
    now = time.time()
    last = self.last_notification_time.get(key, 0)
    if now - last > threshold:
        self.last_notification_time[key] = now
        return True
    return False
```

### 7. **缺少数据缓存**
**问题**: API 失败时界面显示错误，上次有效数据丢失
**建议**: 保留最后一次成功的数据
```python
def __init__(self):
    self.last_valid_data = None

def update_ui(self, data):
    self.last_valid_data = data  # 保存有效数据
```

### 8. **网络请求优化**
**位置**: 第174行
**问题**:
- timeout=10 太长
- 没有重试机制
- 没有连接池复用

**建议**:
```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def __init__(self):
    self.session = requests.Session()
    retry = Retry(total=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    self.session.mount('https://', adapter)

# 使用 self.session.get() 替代 requests.get()
```

### 9. **重复代码**
**位置**: format_time_remaining 和 format_time_short 有 90% 相同代码
**建议**: 提取共同逻辑
```python
def _parse_time_remaining(self, reset_time_str):
    """解析剩余时间（内部方法）"""
    if not reset_time_str:
        return None
    reset_time = datetime.fromisoformat(reset_time_str.replace('+00:00', '+0000'))
    now = datetime.now(timezone.utc)
    return reset_time - now
```

### 10. **Magic Numbers**
**问题**: 硬编码的数字没有命名
**建议**: 定义常量
```python
# 在类开头定义常量
REFRESH_INTERVAL = 60  # 秒
USAGE_WARNING_THRESHOLD = 95
USAGE_HIGH_THRESHOLD = 90
USAGE_MEDIUM_THRESHOLD = 70
REQUEST_TIMEOUT = 5
```

### 11. **长方法**
**位置**: `update_ui()` - 第195-282行 (88行)
**问题**: 违反单一职责原则
**建议**: 拆分为多个方法
```python
def update_ui(self, data):
    self._update_five_hour(data)
    self._update_seven_day(data)
    self._update_opus(data)
    self._check_and_notify(data)
```

---

## 🔵 代码质量改进

### 12. **缺少类型注解**
**建议**: 添加 type hints 提高代码可维护性
```python
from typing import Optional, Dict, Any

def load_config(self) -> None:
def format_time_remaining(self, reset_time_str: Optional[str]) -> str:
```

### 13. **菜单项硬编码**
**位置**: 多处使用 `self.menu["⏱️  5小时限制: 加载中..."]`
**问题**: 字符串魔法值，容易出错
**建议**: 使用常量或属性
```python
def __init__(self):
    self.menu_five_hour = rumps.MenuItem("⏱️  5小时限制: 加载中...", callback=None)
    self.menu_seven_day = rumps.MenuItem("📅 7天限制: 加载中...", callback=None)
```

### 14. **emoji 逻辑重复**
**位置**: 第212-217, 232-237, 255-260行
**建议**: 提取方法
```python
def get_usage_emoji(self, utilization: int) -> str:
    if utilization >= 90:
        return "🔴"
    elif utilization >= 70:
        return "🟡"
    return "🟢"
```

### 15. **错误处理不够细致**
**位置**: 第190-193行
**问题**: 捕获所有异常，难以调试
**建议**: 分别处理不同类型的异常
```python
except requests.Timeout:
    self.title = "⏱️"
    self.menu_five_hour.title = "错误: 请求超时"
except requests.ConnectionError:
    self.title = "📡"
    self.menu_five_hour.title = "错误: 网络连接失败"
except Exception as e:
    self.title = "❌"
    print(f"未预期的错误: {e}")
```

---

## 🛡️ 额外安全建议

### 16. **SSL 验证**
虽然 requests 默认验证 SSL，但建议显式声明：
```python
response = requests.get(url, headers=headers, timeout=5, verify=True)
```

### 17. **配置文件原子写入**
避免写入失败导致配置丢失：
```python
import tempfile
import shutil

def save_config(self):
    config = {'cookie': self.cookie, 'org_id': self.org_id}
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    os.chmod(temp_path, 0o600)
    shutil.move(temp_path, self.config_file)
```

---

## 📊 优先级建议

### 立即修复（高优先级）：
1. ✅ 配置文件权限 (600)
2. ✅ 通知防重复机制
3. ✅ JSON 解析错误处理

### 短期优化（中优先级）：
4. 使用 macOS Keychain 存储 Cookie
5. 添加数据缓存
6. 输入验证
7. 提取常量

### 长期改进（低优先级）：
8. 添加类型注解
9. 重构长方法
10. 代码复用优化

---

## 🎯 总结

**当前代码状态**: ✅ 功能完整，运行正常
**安全评级**: ⚠️ 有安全风险但可控
**代码质量**: 👍 良好，有改进空间

**最关键问题**:
1. Cookie 明文存储且权限过宽
2. 通知重复发送

**建议**: 先实施前3个高优先级修复，然后逐步优化。
