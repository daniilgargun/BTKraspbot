import time
import psutil
import asyncio
from datetime import datetime
from collections import deque
from typing import Dict, List
from bot.config import logger

class PerformanceMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.request_times = deque(maxlen=1000)  # Хранить последние 1000 запросов
        self.error_count = 0
        self.request_count = 0
        self.slow_requests = deque(maxlen=100)  # Хранить 100 самых медленных запросов
        self.metrics = {
            'cpu_usage': deque(maxlen=60),  # Хранить данные за последний час
            'memory_usage': deque(maxlen=60),
            'response_times': deque(maxlen=60),
        }
        
    def add_request_time(self, route: str, duration: float):
        """Добавление времени выполнения запроса"""
        self.request_times.append(duration)
        self.request_count += 1
        
        # Отслеживаем медленные запросы (более 1 секунды)
        if duration > 1.0:
            self.slow_requests.append({
                'route': route,
                'duration': duration,
                'timestamp': datetime.now()
            })
            logger.warning(f"Slow request detected: {route} took {duration:.2f}s")

    def add_error(self, error_type: str, details: str):
        """Регистрация ошибки"""
        self.error_count += 1
        logger.error(f"Error occurred: {error_type} - {details}")

    async def collect_metrics(self):
        """Сбор метрик производительности"""
        try:
            process = psutil.Process()
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            self.metrics['cpu_usage'].append({
                'value': cpu_percent,
                'timestamp': datetime.now()
            })
            
            # Memory usage
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            self.metrics['memory_usage'].append({
                'value': memory_percent,
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'timestamp': datetime.now()
            })
            
            # Average response time
            if self.request_times:
                avg_response_time = sum(self.request_times) / len(self.request_times)
                self.metrics['response_times'].append({
                    'value': avg_response_time,
                    'timestamp': datetime.now()
                })
                
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    def get_performance_report(self) -> Dict:
        """Получение отчета о производительности"""
        uptime = datetime.now() - self.start_time
        
        # Расчет средних значений
        avg_response_time = (
            sum(self.request_times) / len(self.request_times)
            if self.request_times else 0
        )
        
        # Последние метрики CPU и памяти
        last_cpu = (
            self.metrics['cpu_usage'][-1]['value']
            if self.metrics['cpu_usage'] else 0
        )
        last_memory = (
            self.metrics['memory_usage'][-1]['value']
            if self.metrics['memory_usage'] else 0
        )
        
        return {
            'uptime': str(uptime),
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': (self.error_count / self.request_count * 100) if self.request_count else 0,
            'avg_response_time': avg_response_time,
            'current_cpu_usage': last_cpu,
            'current_memory_usage': last_memory,
            'slow_requests_count': len(self.slow_requests)
        }

# Создаем глобальный экземпляр монитора
monitor = PerformanceMonitor() 