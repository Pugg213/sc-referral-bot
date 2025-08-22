"""
Сервис проверки комментариев в Telegram каналах через Telethon
"""
import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, cast
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import ChannelPrivateError, FloodWaitError, UserNotParticipantError, AuthKeyDuplicatedError
from telethon.types import Channel

class CommentChecker:
    """Сервис для проверки комментариев пользователей в каналах"""
    
    def __init__(self):
        self.client = None
        self.last_init_attempt = None
        self.init_retry_delay = 300  # 5 минут между попытками переподключения
        self.is_permanently_disabled = False
        
        api_id_str = os.getenv('TG_API_ID')
        self.api_id = int(api_id_str) if api_id_str else None
        self.api_hash = os.getenv('TG_API_HASH')
        self.session_string = os.getenv('SESSION_STRING')  # Строка сессии из секретов
    
    async def init_client(self):
        """Инициализация Telethon клиента с StringSession с защитой от частых переподключений"""
        # Проверяем не отключена ли система навсегда
        if self.is_permanently_disabled:
            return False
            
        # Проверяем задержку между попытками
        now = datetime.now()
        if self.last_init_attempt and (now - self.last_init_attempt).total_seconds() < self.init_retry_delay:
            return False
            
        self.last_init_attempt = now
        
        if not self.api_id or not self.api_hash:
            logging.warning("TG_API_ID или TG_API_HASH не установлены - проверка комментариев недоступна")
            self.is_permanently_disabled = True
            return False
        
        if not self.session_string:
            logging.warning("SESSION_STRING не установлена - проверка комментариев недоступна")
            logging.info("💡 Добавьте SESSION_STRING в секреты Replit для работы проверки комментариев")
            self.is_permanently_disabled = True
            return False
        
        try:
            # Если клиент уже существует, просто проверяем соединение
            if self.client and self.client.is_connected():
                try:
                    is_auth = await self.client.is_user_authorized()
                    if is_auth:
                        logging.debug("🔧 Telethon клиент уже подключен и авторизован")
                        return True
                except:
                    # Если проверка не удалась, пересоздаем клиент
                    await self.close()
            
            # Создаем клиент с СТАБИЛЬНЫМИ настройками для предотвращения компрометации
            self.client = TelegramClient(
                StringSession(self.session_string), 
                self.api_id, 
                self.api_hash,
                # КРИТИЧНО: Стабильные настройки устройства предотвращают компрометацию
                device_model="Replit Server",
                system_version="Linux",
                app_version="1.0",
                lang_code="ru",
                system_lang_code="ru",
                # Настройки подключения для стабильности
                connection_retries=3,
                retry_delay=5,
                # Использовать только один сервер для предотвращения проблем с IP
                use_ipv6=False
            )
            
            # Подключаемся с таймаутом
            try:
                await asyncio.wait_for(self.client.connect(), timeout=30)
            except asyncio.TimeoutError:
                logging.error("❌ Таймаут подключения к Telegram")
                await self.close()
                return False
            
            # Проверяем авторизацию  
            if not await self.client.is_user_authorized():
                logging.warning("🔧 Строка сессии недействительна - проверка комментариев недоступна")
                logging.info("💡 Создайте новую SESSION_STRING с помощью генератора")
                if self.client:
                    await self.client.disconnect()
                self.client = None
                return False
            
            # КРИТИЧНО: Сбрасываем флаг отключения при успешном подключении
            self.is_permanently_disabled = False
            logging.info("✅ Telethon клиент стабильно подключен (защищен от компрометации)")
            logging.info("🔄 Проверка комментариев восстановлена - система готова к работе")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "authorization key" in error_msg and "ip addresses" in error_msg:
                logging.error("🔑 SESSION_STRING скомпрометирован - сессия использовалась с разных IP адресов")
                logging.error("💡 РЕШЕНИЕ: Создайте новый SESSION_STRING через генератор сессий Telegram")
                logging.error("⚠️ Проверка комментариев отключена до обновления SESSION_STRING")
                self.is_permanently_disabled = True
            elif "authkeyduplicated" in error_msg:
                logging.error("🔑 SESSION_STRING используется в другом месте одновременно")
                logging.error("💡 РЕШЕНИЕ: Убедитесь что SESSION_STRING используется только в одном месте")
                # Не отключаем навсегда - может решиться само
            else:
                logging.error(f"❌ Failed to initialize Telethon client: {e}")
                # Временная ошибка - не отключаем навсегда
            
            self.client = None
            return False
    
    async def check_user_comments_in_channel(self, user_id: int, channel_username: str, 
                                           min_comments: int, period_days: int, 
                                           start_date: datetime, min_posts: int = 1) -> Dict[str, Any]:
        """
        Проверить количество комментариев пользователя в канале за период
        
        Args:
            user_id: ID пользователя Telegram
            channel_username: Username канала (например, @simplecoin_news)
            min_comments: Минимальное количество комментариев
            period_days: Период в днях
            start_date: Дата начала задания
            min_posts: Минимальное количество постов с комментариями
        
        Returns:
            Dict с результатами: success, found_comments, found_posts, meets_requirement, error
        """
        if not self.client:
            # Попытаться переподключиться если не отключено навсегда
            if not self.is_permanently_disabled:
                init_success = await self.init_client()
                if not init_success or not self.client:
                    return {
                        "success": False,
                        "error": "Проверка комментариев временно недоступна. Попробуйте позже.",
                        "found_comments": 0,
                        "meets_requirement": False
                    }
            else:
                return {
                    "success": False,
                    "error": "Проверка комментариев отключена. Обновите SESSION_STRING в настройках.",
                    "found_comments": 0,
                    "meets_requirement": False
                }
        
        # Проверяем что клиент подключен и авторизован
        try:
            if not self.client.is_connected():
                await self.client.connect()
            
            if not await self.client.is_user_authorized():
                return {
                    "success": False,
                    "error": "Требуется авторизация пользователя для проверки комментариев",
                    "found_comments": 0,
                    "meets_requirement": False
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка подключения Telethon: {str(e)[:100]}",
                "found_comments": 0,
                "meets_requirement": False
            }
        
        logging.info(f"🔍 Проверяю комментарии user {user_id} в {channel_username} с {start_date} (нужно {min_comments} комментариев на {min_posts} постах)")
        
        try:
            # Получаем entity канала
            channel = await self.client.get_entity(channel_username)
            if not channel:
                return {
                    "success": False,
                    "error": "Не удалось получить информацию о канале",
                    "found_comments": 0,
                    "meets_requirement": False
                }
            
            # Рассчитываем временной диапазон
            end_date = start_date + timedelta(days=period_days)
            now = datetime.now()
            search_end = min(end_date, now)
            
            # ИСПРАВЛЕНИЕ TIMEZONE: Делаем даты timezone-naive для корректного сравнения
            if hasattr(start_date, 'replace') and start_date.tzinfo:
                start_date = start_date.replace(tzinfo=None)
            if hasattr(search_end, 'replace') and search_end.tzinfo:
                search_end = search_end.replace(tzinfo=None)
            
            # Получаем комментарии пользователя
            comments_count = 0
            posts_with_comments = 0  # Количество постов где пользователь оставил комментарии
            
            logging.info(f"🔍 Проверяю комментарии user {user_id} в {channel_username} с {start_date} по {search_end}")
            logging.info(f"🏷️ Тип канала: {type(channel).__name__}, ID: {channel.id}, Title: {getattr(channel, 'title', 'Unknown')}")
            
            posts_checked = 0  # Счетчик проверенных постов
            
            # Итерируемся по сообщениям в канале
            # ИСПРАВЛЕНИЕ: Ищем посты в разумном диапазоне, но комментарии проверяем по датам
            async for message in self.client.iter_messages(
                entity=cast(Channel, channel), 
                limit=1000  # Ограничиваем поиск для производительности
            ):
                # Пропускаем слишком новые сообщения
                # ИСПРАВЛЕНИЕ TIMEZONE: Приводим дату сообщения к timezone-naive
                message_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
                if message_date > search_end:
                    continue
                
                # ВАЖНО: Не ограничиваем по start_date для постов,
                # т.к. комментарии могут быть оставлены позже чем пост создан
                
                posts_checked += 1
                logging.debug(f"📍 Проверяю пост {message.id} от {message.date}, replies={getattr(message, 'replies', 'None')}")
                
                # Получаем комментарии к этому посту
                post_comments_count = 0
                comments_found_in_post = 0  # Общее количество комментариев в посте
                
                try:
                    async for comment in self.client.iter_messages(
                        entity=cast(Channel, channel),
                        reply_to=message.id,
                        limit=100
                    ):
                        comments_found_in_post += 1
                        logging.debug(f"🔍 Комментарий {comment.id} от user {comment.sender_id} к посту {message.id}")
                        
                        # ИСПРАВЛЕНИЕ: Проверяем дату комментария, а не поста!
                        # Приводим дату комментария к timezone-naive для сравнения
                        comment_date = comment.date.replace(tzinfo=None) if comment.date.tzinfo else comment.date
                        if comment.sender_id == user_id and start_date <= comment_date <= search_end:
                            comments_count += 1
                            post_comments_count += 1
                            logging.info(f"✅ НАЙДЕН комментарий от user {user_id} к посту {message.id} от {comment.date} в {channel_username}!")
                    
                    logging.debug(f"📊 Пост {message.id}: всего комментариев {comments_found_in_post}, от нашего пользователя {post_comments_count}")
                    
                    # Если пользователь оставил хотя бы один комментарий на этот пост
                    if post_comments_count > 0:
                        posts_with_comments += 1
                        logging.info(f"📝 User {user_id} прокомментировал пост {message.id} ({post_comments_count} комментариев)")
                    
                    # Если достигли обоих требований - можно прекратить поиск 
                    if comments_count >= min_comments and posts_with_comments >= min_posts:
                        break
                        
                except Exception as e:
                    logging.info(f"⚠️ Ошибка получения комментариев к посту {message.id}: {e}")
                    continue
            
            # Проверяем оба условия: количество комментариев И количество постов
            meets_comments_requirement = comments_count >= min_comments
            meets_posts_requirement = posts_with_comments >= min_posts
            meets_requirement = meets_comments_requirement and meets_posts_requirement
            
            logging.info(f"📊 ИТОГИ для user {user_id} в {channel_username}:")
            logging.info(f"   🔍 Проверено постов: {posts_checked}")  
            logging.info(f"   💬 Найдено комментариев: {comments_count} (нужно {min_comments})")
            logging.info(f"   📝 Постов с комментариями: {posts_with_comments} (нужно {min_posts})")
            logging.info(f"   ✅ Требования выполнены: {meets_requirement}")
            
            return {
                "success": True,
                "found_comments": comments_count,
                "found_posts": posts_with_comments,
                "meets_requirement": meets_requirement,
                "error": None
            }
            
        except ChannelPrivateError:
            return {
                "success": False,
                "error": "Канал приватный или недоступен",
                "found_comments": 0,
                "found_posts": 0,
                "meets_requirement": False
            }
        except UserNotParticipantError:
            return {
                "success": False,
                "error": "Пользователь не является участником канала",
                "found_comments": 0,
                "found_posts": 0,
                "meets_requirement": False
            }
        except FloodWaitError as e:
            return {
                "success": False,
                "error": f"Превышен лимит запросов. Ожидание {e.seconds} секунд",
                "found_comments": 0,
                "found_posts": 0,
                "meets_requirement": False
            }
        except Exception as e:
            logging.error(f"❌ Ошибка проверки комментариев: {e}")
            return {
                "success": False,
                "error": f"Техническая ошибка: {str(e)}",
                "found_comments": 0,
                "found_posts": 0,
                "meets_requirement": False
            }
    
    async def close(self):
        """ПРАВИЛЬНО закрыть клиент для предотвращения компрометации сессии"""
        if self.client:
            try:
                if hasattr(self.client, 'disconnect') and callable(self.client.disconnect):
                    # Правильно закрываем соединение
                    await self.client.disconnect()
                    logging.info("✅ Telethon клиент корректно отключен (сессия защищена)")
            except Exception as e:
                logging.warning(f"⚠️ Предупреждение при закрытии Telethon: {e}")
            finally:
                self.client = None

# Глобальный экземпляр для использования в приложении
comment_checker = CommentChecker()

async def init_comment_checker():
    """Инициализация глобального экземпляра"""
    return await comment_checker.init_client()