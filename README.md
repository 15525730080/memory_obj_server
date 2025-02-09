# memory_obj_server
基于内存的python对象共享池，用于单机多进程服务python对象共享


Memory based Python object sharing pool for single machine multi process service Python object sharing


# quick start
    pip install -U memory-obj-server 
    ------------------------------------------------
    from memory_obj_server import ObjectStoreService, ObjectStoreClient
    ObjectStoreService.start_server() 
    client = ObjectStoreClient()
    client.put('obj', {'a': 1, 'b': 2})
    client.get('obj')
    client.put('obj', {'c': 3})
    client.get('obj')
    client.delete('obj')
    client.get('obj')
    ObjectStoreService.stop_server()
    ------------------------------------------------
    with ObjectStoreClient() as client_ctx:
        client_ctx.put('hello', 'world')
        print("client get hello:", client_ctx.get('hello'))


# 多进程共享python对象 
![image](https://github.com/user-attachments/assets/5163a03c-b870-487d-8fae-15d00623d7d4)

    import time
    from multiprocessing import Process, freeze_support
    import os
    from memory_obj_server import ObjectStoreService, ObjectStoreClient
    
    # 启动对象存储服务
    ObjectStoreService.start_server()
    
    # 将 UserInfo 类移到全局作用域，提高代码复用性
    class UserInfo:
        def __init__(self, age=20, height=175, weight=130):
            """
            构造函数，用于初始化用户信息
            :param age: 用户年龄，默认为 20
            :param height: 用户身高，默认为 175
            :param weight: 用户体重，默认为 130
            """
            self.age = age
            self.height = height
            self.weight = weight
    
        def update_age(self, new_age):
            """
            更新用户的年龄
            :param new_age: 新的年龄
            """
            if isinstance(new_age, int) and new_age > 0:
                self.age = new_age
            else:
                print("输入的年龄不合法，请输入一个正整数。")
    
        def update_height(self, new_height):
            """
            更新用户的身高
            :param new_height: 新的身高
            """
            if isinstance(new_height, (int, float)) and new_height > 0:
                self.height = new_height
            else:
                print("输入的身高不合法，请输入一个正数。")
    
        def update_weight(self, new_weight):
            """
            更新用户的体重
            :param new_weight: 新的体重
            """
            if isinstance(new_weight, (int, float)) and new_weight > 0:
                self.weight = new_weight
            else:
                print("输入的体重不合法，请输入一个正数。")
    
        def display_info(self):
            """
            显示用户的信息
            """
            print(f"当前进程id: {os.getpid()}")
            print(f"年龄: {self.age} 岁")
            print(f"身高: {self.height} 厘米")
            print(f"体重: {self.weight} 斤")
    
    def set_user_info():
        try:
            # 创建 UserInfo 对象
            user = UserInfo()
            # 创建对象存储客户端
            client = ObjectStoreClient()
            # 将用户信息存入对象存储
            client.put('user', user)
            # 显示用户信息
            user.display_info()
            print("set")
            # 等待 10 秒
            time.sleep(7)
            print("other process set after")
            user = client.get('user')
            user.display_info()    
            time.sleep(10)   
        except Exception as e:
            print(f"set_user_info 函数出现异常: {e}")
    
    def get_user_info():
        try:
            # 创建对象存储客户端
            client = ObjectStoreClient()
            # 从对象存储中获取用户信息
            user = client.get('user')
            # 显示用户信息
            user.display_info()
            # 更新用户信息
            user.update_age(22)
            user.update_height(178)
            user.update_weight(135)
            # 再次显示更新后的用户信息
            # 等待 3 秒
            # 将更新后的用户信息存入对象存储
            client.put('user', user)
            # 等待 10 秒
            time.sleep(10)
        except Exception as e:
            print(f"get_user_info 函数出现异常: {e}")
    
    if __name__ == '__main__':
        freeze_support()
        # 创建设置用户信息的进程
        p1 = Process(target=set_user_info)
        # 创建获取用户信息的进程
        p2 = Process(target=get_user_info)
        # 启动设置用户信息的进程
        p1.start()
        # 等待 3 秒后启动获取用户信息的进程
        time.sleep(3)
        p2.start()
        # 等待 p1 进程完成
        p1.join()
        # 等待 p2 进程完成
        p2.join()
        print("所有子进程已完成。")
            
        
