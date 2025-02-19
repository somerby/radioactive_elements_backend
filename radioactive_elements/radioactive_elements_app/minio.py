from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile

def deleteImg(url):
    client = Minio(
            endpoint = '127.0.0.1:9000',
            access_key = 'minio',
            secret_key = 'minio124',
            secure = False
        )
    if url == '':
        return 'success'
    try:
        url_parts = url.split('/')
        bucket_name = url_parts[-3]
        img_name = '/'.join(url_parts[-2:])
    except:
        return 'error'

    try:
        client.remove_object(bucket_name, img_name)
        return 'success'
    except:
        return 'error'
    
def addImg(img):
    client = Minio(
        endpoint = '127.0.0.1:9000',
        access_key = 'minio',
        secret_key = 'minio124',
        secure = False
    )

    client.put_object(
        'images',
        f'elements/{img.name}',
        img,
        img.size
    )
    return f'http://127.0.0.1:9000/images/elements/{img.name}'