import os
import json
import aiofiles
import asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.DAILIES_CHANNEL_ID = int(os.getenv('DAILIES_CHANNEL_ID', 0))
        self.GUILD_ID = int(os.getenv('GUILD_ID', 0))
        self.PRODUCT_TEAM_ROLES = [int(role_id.strip()) for role_id in os.getenv('PRODUCT_TEAM_ROLES', '').split(',') if role_id.strip()]
        self.ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID', 0))
        self.TIMEZONE = os.getenv('TIMEZONE', 'America/Buenos_Aires')
        self.DAILY_HOUR = int(os.getenv('DAILY_HOUR', 10))
        self.DAILY_MINUTE = int(os.getenv('DAILY_MINUTE', 0))
        
        self.DATA_DIR = 'data'
        self.SCHEDULE_FILE = os.path.join(self.DATA_DIR, 'schedule.json')
        self.DAILIES_FILE = os.path.join(self.DATA_DIR, 'dailies.json')
        self.MESSAGES_FILE = os.path.join(self.DATA_DIR, 'messages.json')
        
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)

class ScheduleManager:
    def __init__(self, config: Config):
        self.config = config
        self.schedule_file = config.SCHEDULE_FILE
        
    async def load_schedule(self) -> Dict:
        default_schedule = {
            "enabled": True,
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "hour": self.config.DAILY_HOUR,
            "minute": self.config.DAILY_MINUTE,
            "custom_schedule": False,
            "reminder_enabled": False,
            "reminder_hour": 14,
            "reminder_minute": 0
        }
        
        try:
            async with aiofiles.open(self.schedule_file, 'r') as f:
                content = await f.read()
                if not content.strip():
                    # Archivo vacío, usar default
                    await self.save_schedule(default_schedule)
                    return default_schedule
                return json.loads(content)
        except FileNotFoundError:
            await self.save_schedule(default_schedule)
            return default_schedule
        except json.JSONDecodeError as e:
            print(f"Error decoding schedule JSON: {e}")
            # Archivo corrupto, recrear con valores por defecto
            await self.save_schedule(default_schedule)
            return default_schedule
        except Exception as e:
            print(f"Error loading schedule: {e}")
            return default_schedule
    
    async def save_schedule(self, schedule: Dict):
        try:
            async with aiofiles.open(self.schedule_file, 'w') as f:
                await f.write(json.dumps(schedule, indent=2))
            return True
        except Exception as e:
            print(f"Error saving schedule: {e}")
            return False
    
    async def update_days(self, days: List[str]):
        schedule = await self.load_schedule()
        schedule['days'] = days
        schedule['custom_schedule'] = True
        return await self.save_schedule(schedule)
    
    async def update_time(self, hour: int, minute: int):
        schedule = await self.load_schedule()
        schedule['hour'] = hour
        schedule['minute'] = minute
        return await self.save_schedule(schedule)
    
    async def toggle_enabled(self, enabled: bool):
        schedule = await self.load_schedule()
        schedule['enabled'] = enabled
        return await self.save_schedule(schedule)
    
    async def update_reminder(self, enabled: bool, hour: int = None, minute: int = None):
        schedule = await self.load_schedule()
        schedule['reminder_enabled'] = enabled
        if hour is not None:
            schedule['reminder_hour'] = hour
        if minute is not None:
            schedule['reminder_minute'] = minute
        return await self.save_schedule(schedule)
    
    async def toggle_reminder_enabled(self, enabled: bool):
        schedule = await self.load_schedule()
        schedule['reminder_enabled'] = enabled
        return await self.save_schedule(schedule)

class DailiesStorage:
    def __init__(self, config: Config):
        self.config = config
        self.dailies_file = config.DAILIES_FILE
        self._lock = asyncio.Lock()  # Lock para evitar condiciones de carrera
    
    async def save_daily(self, user_id: int, guild_id: int, daily_data: Dict):
        async with self._lock:  # Usar lock para evitar condiciones de carrera
            try:
                # Intentar cargar dailies existentes
                dailies = {}
                try:
                    async with aiofiles.open(self.dailies_file, 'r') as f:
                        content = await f.read()
                        if content.strip():  # Solo parsear si el archivo no está vacío
                            dailies = json.loads(content)
                except FileNotFoundError:
                    # Archivo no existe, usar diccionario vacío
                    dailies = {}
                except json.JSONDecodeError as e:
                    print(f"Warning: Corrupted dailies file, starting fresh. Error: {e}")
                    # Archivo corrupto, hacer backup y empezar de nuevo
                    import shutil
                    from datetime import datetime
                    backup_name = f"{self.dailies_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        shutil.copy2(self.dailies_file, backup_name)
                        print(f"Backup created: {backup_name}")
                    except:
                        pass
                    dailies = {}
                
                from datetime import datetime
                import pytz
                
                tz = pytz.timezone(self.config.TIMEZONE)
                today = datetime.now(tz).strftime('%Y-%m-%d')
                
                # Asegurar estructura del diccionario
                if today not in dailies:
                    dailies[today] = {}
                
                if str(guild_id) not in dailies[today]:
                    dailies[today][str(guild_id)] = {}
                
                # Verificar si ya existe una daily para este usuario hoy
                if str(user_id) in dailies[today][str(guild_id)]:
                    print(f"User {user_id} already has a daily for today")
                    return False  # Ya existe una daily
                
                dailies[today][str(guild_id)][str(user_id)] = {
                    **daily_data,
                    'timestamp': datetime.now(tz).isoformat()
                }
                
                # Guardar con manejo de errores
                async with aiofiles.open(self.dailies_file, 'w') as f:
                    await f.write(json.dumps(dailies, indent=2, ensure_ascii=False))
                
                return True
            except Exception as e:
                print(f"Error saving daily: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    async def get_today_dailies(self, guild_id: int) -> Dict:
        try:
            async with aiofiles.open(self.dailies_file, 'r') as f:
                content = await f.read()
                if not content.strip():  # Archivo vacío
                    return {}
                dailies = json.loads(content)
            
            from datetime import datetime
            import pytz
            
            tz = pytz.timezone(self.config.TIMEZONE)
            today = datetime.now(tz).strftime('%Y-%m-%d')
            
            if today in dailies and str(guild_id) in dailies[today]:
                return dailies[today][str(guild_id)]
            
            return {}
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"Warning: Corrupted dailies file when reading. Error: {e}")
            return {}
        except Exception as e:
            print(f"Error getting dailies: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def has_submitted_today(self, user_id: int, guild_id: int) -> bool:
        dailies = await self.get_today_dailies(guild_id)
        return str(user_id) in dailies

    async def clear_all_dailies(self):
        """Limpia completamente el archivo de dailies"""
        async with self._lock:
            try:
                async with aiofiles.open(self.dailies_file, 'w') as f:
                    await f.write('{}')
                return True
            except Exception as e:
                print(f"Error clearing dailies: {e}")
                return False

class DailyMessagesStorage:
    def __init__(self, config: Config):
        self.config = config
        self.messages_file = config.MESSAGES_FILE
        self._lock = asyncio.Lock()

    async def _read_all(self):
        try:
            async with aiofiles.open(self.messages_file, 'r') as f:
                content = await f.read()
                if not content.strip():
                    return {}
                return json.loads(content)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"Error reading messages store: {e}")
            return {}

    async def _write_all(self, data: dict) -> bool:
        try:
            async with aiofiles.open(self.messages_file, 'w') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"Error writing messages store: {e}")
            return False

    async def save_message(self, user_id: int, guild_id: int, channel_id: int, message_id: int, date_str: str) -> bool:
        async with self._lock:
            data = await self._read_all()
            if date_str not in data:
                data[date_str] = {}
            if str(guild_id) not in data[date_str]:
                data[date_str][str(guild_id)] = {}
            data[date_str][str(guild_id)][str(user_id)] = {
                'channel_id': int(channel_id),
                'message_id': int(message_id),
                'disabled': bool(data[date_str][str(guild_id)].get(str(user_id), {}).get('disabled', False))
            }
            return await self._write_all(data)

    async def list_all(self) -> dict:
        return await self._read_all()

    async def list_for_date(self, date_str: str) -> dict:
        data = await self._read_all()
        return data.get(date_str, {})

    async def mark_disabled(self, user_id: int, guild_id: int, date_str: str) -> bool:
        async with self._lock:
            data = await self._read_all()
            try:
                if date_str in data and str(guild_id) in data[date_str] and str(user_id) in data[date_str][str(guild_id)]:
                    data[date_str][str(guild_id)][str(user_id)]['disabled'] = True
                    return await self._write_all(data)
            except Exception:
                pass
            return False

    async def delete_date(self, date_str: str) -> bool:
        async with self._lock:
            data = await self._read_all()
            if date_str in data:
                del data[date_str]
                return await self._write_all(data)
            return True

def sort_days(days: list) -> list:
    """Ordena los días de la semana en orden cronológico"""
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return sorted(days, key=lambda x: day_order.index(x) if x in day_order else 999)

def format_days_spanish(days: list) -> str:
    """Convierte y ordena días al español"""
    days_map = {
        'monday': 'Lunes',
        'tuesday': 'Martes',
        'wednesday': 'Miércoles',
        'thursday': 'Jueves',
        'friday': 'Viernes',
        'saturday': 'Sábado',
        'sunday': 'Domingo'
    }

    sorted_days = sort_days(days)
    return ", ".join([days_map.get(day, day.capitalize()) for day in sorted_days])

config = Config()
schedule_manager = ScheduleManager(config)
dailies_storage = DailiesStorage(config)
messages_storage = DailyMessagesStorage(config)