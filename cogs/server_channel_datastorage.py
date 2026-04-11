from dataclasses import dataclass , field



@dataclass
class Channel:
    channel_id:int
    owner_id:int
    server_id:int
    category_id:int

    def get_channel_id(self)->int:
        return self.channel_id
    
    def get_owner_id(self)->int:
        return self.owner_id

    def get_server_id(self)->int:
        return self.server_id
    
    def get_category_id(self)->int:
        return self.category_id



class Server:
    server_id:int
    category_id:int
    # channel id -> channel
    channels:dict[int,Channel] = field(default_factory=dict) # feild() to create new in memory dictonary for each server instance 

    def get_server_id(self)->int:
        return self.server_id
    
    def get_category_id(self)->int:
        return self.category_id