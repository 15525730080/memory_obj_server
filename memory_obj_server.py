import threading
import subprocess
import platform
import rpyc
import dill
import logging
from rpyc.utils.server import ThreadedServer
from filelock import FileLock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PortManager:
    """Handles the release of network ports."""

    @staticmethod
    def release_port(port):
        sys = platform.system()
        try:
            if sys == 'Windows':
                find_cmd = f'netstat -ano | findstr :{port}'
                pid = subprocess.run(find_cmd, shell=True, capture_output=True, text=True).stdout.strip().split()[-1:]
                if pid:
                    subprocess.run(f'taskkill /F /PID {pid[0]}', shell=True, check=True)
                    logger.info(f'Port {port} successfully released')
                else:
                    logger.info(f'Port {port} is not occupied')
            elif sys in ['Linux', 'Darwin']:
                find_cmd = f'lsof -t -i:{port}'
                pid = subprocess.run(find_cmd, shell=True, capture_output=True, text=True).stdout.strip()
                if pid:
                    subprocess.run(f'kill -9 {pid}', shell=True, check=True)
                    logger.info(f'Port {port} successfully released')
                else:
                    logger.info(f'Port {port} is not occupied')
            else:
                logger.warning(f'Unsupported operating system: {sys}')
        except (subprocess.CalledProcessError, IndexError):
            logger.error(f'Error releasing port {port}')


class ObjectStoreService(rpyc.Service):
    """RPyC service for storing, retrieving, and deleting objects."""
    storage = dict()
    real_server_thread = None
    server_instance = None
    storage_lock = threading.Lock()
    server_lock = FileLock("server.lock")  # 服务启动保证当前机器唯一性

    @classmethod
    def exposed_put(cls, key, value: str):
        """Stores an object under a specified key."""
        with cls.storage_lock:
            try:
                cls.storage[key] = value
                logger.info(f"Object stored under key '{key}'.")
                return f"Object stored under key '{key}'."
            except Exception as e:
                logger.error(f"Error storing object: {e}")
                return f"Error storing object: {e}"

    @classmethod
    def exposed_get(cls, key):
        """Retrieves an object by its key."""
        with cls.storage_lock:
            try:
                serialized_obj = cls.storage.get(key, None)
                logger.info(f"Retrieved object under key '{key}'.")
                return serialized_obj
            except Exception as e:
                logger.error(f"Error retrieving object: {e}")
                return f"Error retrieving object: {e}"

    @classmethod
    def exposed_delete(cls, key):
        """Deletes an object by its key."""
        with cls.storage_lock:
            try:
                if key in cls.storage:
                    del cls.storage[key]
                    logger.info(f"Object deleted under key '{key}'.")
                    return f"Object deleted under key '{key}'."
                else:
                    logger.warning(f"Key '{key}' not found.")
                    return f"Key '{key}' not found."
            except Exception as e:
                logger.error(f"Error deleting object: {e}")
                return f"Error deleting object: {e}"

    @classmethod
    def start_server(cls, port=6000):
        """Starts the RPyC server."""
        with cls.server_lock:
            if not cls.real_server_thread:
                try:
                    PortManager.release_port(port)
                    cls.server_instance = ThreadedServer(cls, port=port)
                    real_server_thread = threading.Thread(target=cls.server_instance.start)
                    real_server_thread.start()
                    cls.real_server_thread = real_server_thread
                    logger.info(f"Server started on port {port}")
                except Exception as e:
                    logger.error(f"Error starting server: {e}")

    @classmethod
    def stop_server(cls):
        """Stops the RPyC server."""
        if cls.server_instance:
            cls.server_instance.close()
            cls.real_server_thread.join()
            cls.real_server_thread = None
            cls.server_instance = None
            logger.info("Server stopped.")

def catch_connection_closed(func):
    def real_func(*args):
        try:
            return func(*args)
        except EOFError:
             logger.error("Server stopped.")
    return real_func
class ObjectStoreClient:
    """Client for interacting with the ObjectStoreService."""

    def __init__(self, host='localhost', port=6000):
        self.conn = rpyc.connect(host, port)
    @catch_connection_closed
    def put(self, key, obj):
        """Stores an object on the server."""
        response = self.conn.root.put(key, dill.dumps(obj))
        logger.info(f"PUT Response: {response}")
    @catch_connection_closed
    def get(self, key):
        """Retrieves an object from the server."""
        response = self.conn.root.get(key)
        if response:
            logger.info(f"GET Response: {response}")
            return dill.loads(response)
        return response
    @catch_connection_closed
    def delete(self, key):
        """Deletes an object from the server."""
        response = self.conn.root.delete(key)
        logger.info(f"DELETE Response: {response}")
    @catch_connection_closed
    def __del__(self):
        """Closes the connection."""
        self.conn.close()


# 示例用法
if __name__ == "__main__":
    ObjectStoreService.start_server()
    ObjectStoreService.start_server()
    
    client = ObjectStoreClient()
    client1 = ObjectStoreClient()
    client2 = ObjectStoreClient()
    client3 = ObjectStoreClient()

    client.put('foo', {'bar': 123})
    client1.put('foo1', {'bar': 1234})
    client2.put('foo2', {'bar': 1235})
    client3.put('foo3', {'bar': 1236})

    print("client3", client3.get('foo'))
    print("client", client.get('foo1'))
    print("client2", client2.get('foo2'))
    print("client1", client1.get('foo3'))

    client1.delete("foo3")
    print("client3", client3.get('foo3'))

    # 停止服务
    ObjectStoreService.stop_server()
    client1.delete("foo3")
