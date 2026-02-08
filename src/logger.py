"""Logging configuration for ReportBot."""
import logging
import os
import sys
import atexit
import traceback
from logging.handlers import RotatingFileHandler

# Logger instance - will be configured on first import
_logger = None
_file_handler = None


class FlushingRotatingFileHandler(RotatingFileHandler):
    """Her log yazımından sonra otomatik flush yapan handler.
    
    Bu sayede uygulama aniden kapansa bile loglar diske yazılır.
    """
    
    def emit(self, record):
        """Log kaydını yaz ve hemen flush yap."""
        super().emit(record)
        self.flush()


def _flush_all_handlers():
    """Tüm handler'ları flush et - uygulama kapanırken çağrılır."""
    if _logger is not None:
        for handler in _logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass


def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Yakalanmamış exception'ları logla ve flush yap.
    
    Bu sayede uygulama crash olduğunda son hata mesajı da log'a yazılır.
    """
    # KeyboardInterrupt için normal çıkış
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Hata mesajını logla
    if _logger is not None:
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        _logger.critical(f"💥 YAKALANMAMIŞ HATA - Uygulama çöktü!\n{error_msg}")
        _flush_all_handlers()
    
    # Orijinal excepthook'u da çağır
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def get_log_directory() -> str:
    """
    Log klasörünün yolunu döndürür.
    
    PyInstaller EXE olarak çalışırken: EXE'nin yanındaki logs/ klasörü
    Normal Python olarak çalışırken: Proje root'undaki logs/ klasörü
    
    Returns:
        Log klasörünün tam yolu.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller EXE olarak çalışıyor
        # sys.executable = EXE'nin tam yolu (örn: C:\Users\sidal\Desktop\ReportBot.exe)
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, 'logs')
    else:
        # Normal Python olarak çalışıyor
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, 'logs')


def setup_logger():
    """Setup and return the application logger."""
    global _logger, _file_handler
    
    if _logger is not None:
        return _logger
    
    # logs klasörünü oluştur
    log_dir = get_log_directory()
    os.makedirs(log_dir, exist_ok=True)
    
    # Tek log dosyası - hep aynı dosyaya yazar
    log_filename = os.path.join(log_dir, 'reportbot.log')
    
    # Log dosyası konumunu başlangıçta göster (debug için)
    print(f"📝 Log dosyası: {log_filename}")
    
    # Logger oluştur
    _logger = logging.getLogger('reportbot')
    _logger.setLevel(logging.DEBUG)
    
    # Eğer handler zaten eklenmişse tekrar ekleme
    if _logger.handlers:
        return _logger
    
    # Dosyaya yazan handler - HER LOG SONRASI FLUSH YAPAR
    # (5MB'dan büyükse yeni dosyaya geçer, 5 eski dosya tutar)
    _file_handler = FlushingRotatingFileHandler(
        log_filename,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,  # reportbot.log.1, .2, .3, .4, .5 şeklinde yedekler
        encoding='utf-8'
    )
    _file_handler.setLevel(logging.DEBUG)
    
    # Console'a yazan handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Log formatı - tarih, seviye ve mesaj
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')  # Console'da sadece mesaj
    
    _file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    _logger.addHandler(_file_handler)
    _logger.addHandler(console_handler)
    
    # Program kapanırken logları flush et
    atexit.register(_flush_all_handlers)
    
    # Yakalanmamış hataları logla
    sys.excepthook = _handle_uncaught_exception
    
    return _logger


# Global logger - import edildiğinde otomatik kurulur
logger = setup_logger()
