""" Paquete para adición de ruido gaussiano a imágenes.
Este script le permite al usuario aplicar ruido gaussiano
a imagenes almacenadas en S3.

Este archivo puede importarse como modulo y contiene las siguientes funciones:

    * list_objects: lista y devuelve los objetos que se encuentran en un 
                    bucket de Amazon S3 y coinciden con un prefijo 
                    específico.
    * add_noise: aplica un efecto de desenfoque gaussiano a una imagen.
    * gaussian_noise: agrega un efecto de ruido gaussiano a 
                    imágenes almacenadas en S3.
"""

import yaml
import boto3
from typing import List
from PIL import Image, ImageFilter
import io
import numpy as np
import cv2 as cv

# Abrir yaml
with open("configs/config.yaml", encoding="utf-8") as file:
    config = yaml.safe_load(file)
file.close()

# Variables globales
PREPROCESSED_TRAIN_PREFIX = config['gaussian']['PREPROCESSED_TRAIN_PREFIX']
PREPROCESSED_VALID_PREFIX = config['gaussian']['PREPROCESSED_VALID_PREFIX']
GAUSSIAN_TRAIN_PREFIX = config['gaussian']['GAUSSIAN_TRAIN_PREFIX']
GAUSSIAN_VALID_PREFIX = config['gaussian']['GAUSSIAN_VALID_PREFIX']
BUCKET_NAME = config['aws_config']['BUCKET_NAME']
S3_PROFILE = config['aws_config']['PROFILE_NAME']

session = boto3.Session(profile_name=S3_PROFILE)
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
                 img_name: str = None,
                 image: np.array = None
            ):
    _, im_buff_arr = cv.imencode(".png", image)
    byte_im = im_buff_arr.tobytes()
    name = f'{prefix}/{img_name}'
    print(name)
    client.put_object(Bucket = bucket_name, Body = byte_im, Key = name)

def add_noise(
              object: str = None,
              image: Image = None,
            ):
    img_name = object.split('/')[-1]
    new_img_name = img_name[:-4] + "_blured" + img_name[-4:]
    blured_img = image.filter(ImageFilter.GaussianBlur(2.3))
    return new_img_name, blured_img


def gaussian_noise(
                    client = None,
                    bucket_name: str = None,
                    prefix: str = None,
                    objects: List[str] = []
                ):
    for object in objects:
        response = client.get_object(Bucket = bucket_name, Key = object)
        image = response['Body'].read()
        image_pil = Image.open(io.BytesIO(image))
        new_img_name, image_blured = add_noise(object, image_pil)
        res_image = np.asarray(image_blured)
        put_image_s3(client, bucket_name, prefix, new_img_name, res_image)
    return True

if __name__ == '__main__':
    train_objects = list_objects(s3_client, BUCKET_NAME, PREPROCESSED_TRAIN_PREFIX)
    train_objects = [obj['Key'] for obj in train_objects]

    valid_objects = list_objects(s3_client, BUCKET_NAME, PREPROCESSED_VALID_PREFIX)
    valid_objects = [obj['Key'] for obj in valid_objects]

    print(gaussian_noise(s3_client, BUCKET_NAME, GAUSSIAN_TRAIN_PREFIX, train_objects))
    print(gaussian_noise(s3_client, BUCKET_NAME, GAUSSIAN_VALID_PREFIX, valid_objects))
