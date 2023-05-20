import boto3
from typing import List
from PIL import Image
import io
import numpy as np
import cv2 as cv

BUCKET_NAME = 'images-itam-denoising-dev'
RAW_TRAIN_PREFIX = f'raw/train'
RAW_VALID_PREFIX = f'raw/valid'
PREPROCESSED_TRAIN_PREFIX = f'preprocessed/train'
PREPROCESSED_VALID_PREFIX = f'preprocessed/valid'

session = boto3.Session(profile_name='datascientist')
s3_client = session.client('s3')

def list_objects(client = None, bucket_name: str = None, prefix: str = None):
    s3_objects = []
    if client:
        try:
            s3_response = client.list_objects_v2(Bucket = bucket_name, Prefix = prefix)
            s3_objects.extend(s3_response['Contents'])
            while s3_response['IsTruncated']:
                next_token = s3_response['NextContinuationToken']
                s3_response = client.list_objects_v2(
                                                     Bucket = bucket_name,
                                                     Prefix = prefix,
                                                     ContinuationToken = next_token
                                                )
                if 'Contents' in s3_response:
                    s3_objects.extend(s3_response['Contents'])
            return s3_objects
        except Exception:
            raise Exception

def prop_black_pixels(image):
    num_black_pixels = np.sum(image <= 30)
    return num_black_pixels / image.size

def put_image_s3(
                 client = None, 
                 bucket_name: str = None,
                 prefix: str = None,
                 image: np.array = None,
                 count_img: int = 0
            ):
    tmp_resized = cv.resize(image, (400,512), interpolation = cv.INTER_AREA)
    _, im_buff_arr = cv.imencode(".png", tmp_resized)
    byte_im = im_buff_arr.tobytes()
    folder = prefix.split('/')[-1]
    name = f'{prefix}/{count_img}_{folder}.png'
    client.put_object(Bucket = bucket_name, Body = byte_im, Key = name)
    print(name)

def preprocess_image(
                    client = None, 
                    bucket_name: str = None,
                    prefix: str = None,
                    image: np.array = None,
                    count_img: int = 0
                    ):
    response = 0
    tmp_image = image.copy()
    pbp = prop_black_pixels(tmp_image)
    if pbp <= 0.6:
        img_shape = tmp_image.shape
        h = img_shape[0]
        w = img_shape[1]
        if w > h:
            tmp_image = cv.rotate(tmp_image, cv.ROTATE_90_CLOCKWISE)
        if w > 250:
            put_image_s3(client, bucket_name, prefix, tmp_image, count_img)
            response = 1
    return response

def preprocess_images(
                      client = None,
                      bucket_name: str = None,
                      prefix: str = None,
                      objects: List[str] = []
                    ):
    count_img = 0
    for object in objects:
        response = client.get_object(Bucket = bucket_name, Key = object)
        image = response['Body'].read()
        image = Image.open(io.BytesIO(image))
        image = np.asarray(image)
        was_image_saved = preprocess_image(client, bucket_name, prefix, image, count_img)
        count_img += was_image_saved
    return count_img

train_objects = list_objects(s3_client, BUCKET_NAME, RAW_TRAIN_PREFIX)
train_objects = [obj['Key'] for obj in train_objects]

valid_objects = list_objects(s3_client, BUCKET_NAME, RAW_VALID_PREFIX)
valid_objects = [obj['Key'] for obj in valid_objects]

print(preprocess_images(s3_client, BUCKET_NAME, PREPROCESSED_TRAIN_PREFIX, train_objects))
print(preprocess_images(s3_client, BUCKET_NAME, PREPROCESSED_VALID_PREFIX, valid_objects))

# response = s3_client.get_object(Bucket = BUCKET_NAME, Key = 'preprocessed/valid/0_valid.png')
# image_content = response['Body'].read()
# image = Image.open(io.BytesIO(image_content))
# image = np.asarray(image)
# print(image)