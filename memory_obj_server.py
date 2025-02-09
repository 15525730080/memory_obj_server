import threading
import subprocess
import platform
import rpyc
import dill
import logging
from rpyc.utils.server import ThreadedServer
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PortManager:
    @staticmethod
    def release_port(port):
        """
        释放占用指定端口的进程。支持 Windows、Linux 和 Darwin 系统。
        """
        sys_type = platform.system()
        try:
            if sys_type == 'Windows':
                find_cmd = f'netstat -ano | findstr :{port}'
                output = subprocess.run(find_cmd, shell=True, capture_output=True, text=True).stdout.strip()
                # 获取所有可能的 PID
                pids = [line.split()[-1] for line in output.splitlines() if line]
                for pid in pids:
                    kill_result = subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True, text=True)
                    kill_result.check_returncode()  # 检查杀死进程命令是否成功执行
                    logger.info(f'Port {port} successfully released (PID {pid})')
            elif sys_type in ['Linux', 'Darwin']:
                find_cmd = f'lsof -t -i:{port}'
                output = subprocess.run(find_cmd, shell=True, capture_output=True, text=True).stdout.strip()
                pids = output.split()
                for pid in pids:
                    kill_result = subprocess.run(f'kill -9 {pid}', shell=True, capture_output=True, text=True)
                    kill_result.check_returncode()  # 检查杀死进程命令是否成功执行
                    logger.info(f'Port {port} successfully released (PID {pid})')
            else:
                logger.warning(f'Unsupported operating system: {sys_type}')
        except subprocess.CalledProcessError:
            logger.error(f'Error releasing port {port}')
        except Exception as e:
            logger.error(f'Unexpected error while releasing port {port}: {e}')

class ObjectStoreService(rpyc.Service):
    """
    RPyC 服务类，用于存储、查询和删除对象。
    """
    storage = dict()
    real_server_thread = None
    server_instance = None
    storage_lock = threading.RLock()
    server_lock = FileLock("server.lock")

    @classmethod
    def exposed_put(cls, key, value):
        """
        存储对象，传入的 value 应为经过 dill 序列化后的数据。
        """
        with cls.storage_lock:
            cls.storage[key] = value
            logger.info(f"Object stored under key '{key}'.")
            return f"Object stored under key '{key}'."

    @classmethod
    def exposed_get(cls, key):
        """
        获取存储的对象数据，返回值为 dill 序列化后的数据或 None。
        """
        with cls.storage_lock:
            return cls.storage.get(key, None)

    @classmethod
    def exposed_delete(cls, key):
        """
        删除存储的对象，如果 key 不存在则返回提示字符串。
        """
        with cls.storage_lock:
            return cls.storage.pop(key, f"Key '{key}' not found.")

    @classmethod
    def start_server(cls, port=30731):
        """
        启动 RPyC 服务。若服务已启动则直接返回。
        """
        with cls.server_lock:
            if cls.real_server_thread:
                logger.info("Server is already running.")
                return
            try:
                PortManager.release_port(port)
                cls.server_instance = ThreadedServer(cls, port=port)
                cls.real_server_thread = threading.Thread(target=cls.server_instance.start, daemon=True)
                cls.real_server_thread.start()
                logger.info(f"Server started on port {port}")
            except Exception as e:
                logger.error(f"Error starting server: {e}")

    @classmethod
    def stop_server(cls):
        """
        停止 RPyC 服务，并清理线程和实例。
        """
        with cls.server_lock:
            if cls.server_instance:
                cls.server_instance.close()
                cls.real_server_thread.join()
                cls.real_server_thread = None
                cls.server_instance = None
                logger.info("Server stopped.")

def catch_connection_closed(func):
    """
    装饰器，用于捕获客户端因连接关闭引发的 EOFError 异常，
    并返回 None。
    """
    def real_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EOFError:
            logger.error("Server connection closed.")
            return None
    return real_func

class ObjectStoreClient:
    """
    客户端类，用于操作 ObjectStoreService 服务。
    支持上下文管理器，以便自动关闭连接。
    """
    def __init__(self, host='localhost', port=30731):
        self.conn = rpyc.connect(host, port)
        logger.info(f"Connected to server at {host}:{port}")

    @catch_connection_closed
    def put(self, key, obj):
        """
        存储对象。内部对对象进行 dill 序列化。
        """
        return self.conn.root.put(key, dill.dumps(obj))

    @catch_connection_closed
    def get(self, key):
        """
        获取对象，并对结果进行反序列化。
        """
        response = self.conn.root.get(key)
        return dill.loads(response) if response else None

    @catch_connection_closed
    def delete(self, key):
        """
        删除对象，返回删除结果。
        """
        return self.conn.root.delete(key)

    def close(self):
        """
        关闭连接，支持多次调用。
        """
        if self.conn:
            self.conn.close()
      
    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
