from enum import Enum
class LogLevel(Enum):
    LOG_INFO=0
    LOG_WARNING=1
def DebugLog(log_level:LogLevel,message):
    if log_level==LogLevel.LOG_INFO:
        print(f"[LOG_INFO]: {message}")
    elif log_level==LogLevel.LOG_WARNING:
        print(f"[LOG_WARNING]: {message}")