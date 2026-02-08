"""Logging configuration for ReportBot."""
import logging
import os
from logging.handlers import RotatingFileHandler

# Logger instance - will be configured on first import
_logger = None


def setup_logger():
    """Setup and return the application logger."""
    global _logger
    
    if _logger is not None:
        return _logger
    
    # logs klasörünü oluştur (proje root'unda)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Tek log dosyası - hep aynı dosyaya yazar
    log_filename = os.path.join(log_dir, 'reportbot.log')
    
    # Logger oluştur
    _logger = logging.getLogger('reportbot')
    _logger.setLevel(logging.DEBUG)
    
    # Eğer handler zaten eklenmişse tekrar ekleme
    if _logger.handlers:
        return _logger
    
    # Dosyaya yazan handler (5MB'dan büyükse yeni dosyaya geçer, 5 eski dosya tutar)
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,  # reportbot.log.1, .2, .3, .4, .5 şeklinde yedekler
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console'a yazan handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Log formatı - tarih, seviye ve mesaj
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')  # Console'da sadece mesaj
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)
    
    return _logger


# Global logger - import edildiğinde otomatik kurulur
logger = setup_logger()
