from typing import Optional
import re

class InputValidator:
    @staticmethod
    def validate_group(group: str) -> bool:
        """Проверка корректности номера группы"""
        pattern = r'^[1-5]\d{2}$|^З-\d{3}$'
        return bool(re.match(pattern, group))
        
    @staticmethod
    def validate_teacher(teacher: str) -> bool:
        """Проверка имени преподавателя"""
        pattern = r'^[А-ЯЁ][а-яё]+ [А-ЯЁ]\.[А-ЯЁ]\.$'
        return bool(re.match(pattern, teacher))
        
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Очистка пользовательского ввода"""
        # Удаляем специальные символы
        text = re.sub(r'[<>&\'"]', '', text)
        return text.strip()
        
    @staticmethod
    def validate_file_id(file_id: str) -> bool:
        """Проверка корректности file_id"""
        return bool(re.match(r'^[A-Za-z0-9_-]+$', file_id)) 