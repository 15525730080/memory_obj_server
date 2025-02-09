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



    
    
