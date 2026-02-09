from bson import ObjectId

def to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)

def oid_str(oid) -> str:
    return str(oid)
