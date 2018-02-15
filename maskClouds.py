#!/usr/bin/python3
#by mquinteiro Feb 2018

import numpy as np
from numpy import subtract, add, divide, multiply
from osgeo import gdal
import datetime

file_endings10 = ["B02","B03","B04","B08"]
file_endings20 = ["B05","B06","B07","B8A"]
now = datetime.datetime.now()
print("Starting: ",now)


def maskFile(origFile,cld_mask_file,scl_mask_file,destFile, factor=2, saveJ2K=False):
    driver = gdal.GetDriverByName("GTiff")
    img = gdal.Open(origFile)
    img_band = img.GetRasterBand(1)
    img_data = img_band.ReadAsArray(0, 0, img.RasterXSize, img.RasterYSize)

    now = datetime.datetime.now()
    print("Duplicating layer: ",now)
    dst_ds = driver.CreateCopy(destFile+".tif", img, strict=0)

    now = datetime.datetime.now()
    print("Reopening for Write: ",now)
    #dst_ds = None
    #dst_ds = gdal.Open(destFile, gdal.GA_Update)
    dst_band = dst_ds.GetRasterBand(1)
    dst_data = dst_band.ReadAsArray(0, 0, img.RasterXSize, img.RasterYSize)
    '''
    dst_ds = driver.Create("test.jp2",xsize=img.RasterXSize, ysize=img.RasterYSize,bands=1,eType=gdal.GDT_UInt16)

    if(dst_ds is None):
        print(gdal.GetLastErrorMsg())
    '''
    cld = gdal.Open(cld_mask_file)
    cld_band = cld.GetRasterBand(1)
    cld_data = cld_band.ReadAsArray(0, 0, cld.RasterXSize, cld.RasterYSize)

    scl = gdal.Open(scl_mask_file)
    scl_band = scl.GetRasterBand(1)
    scl_data = scl_band.ReadAsArray(0, 0, scl.RasterXSize, scl.RasterYSize)

    mods=0

    now = datetime.datetime.now()
    print("Making mask: ",now)

    logic = np.logical_and(cld_data==0,np.logical_or(scl_data==4,scl_data==5))
    if factor ==2 :
        big_logic= np.empty((logic.shape[0]*factor,logic.shape[1]*factor),dtype=bool)
        big_logic[::2,::2]=logic
        big_logic[::2,1::2]=big_logic[::2,::2]
        big_logic[1::2,:]=big_logic[::2,:]
    elif factor==1 :
        big_logic = np.empty((logic.shape[0], logic.shape[1]), dtype=bool)
        big_logic = logic
    else:
        print("Wrong scale factor. Factor must be 2 for 10m or 1 for 60m")
        return
    dst_data=np.multiply(dst_data,big_logic)
    dst_data=dst_data+65535*np.logical_not(big_logic)
    now = datetime.datetime.now()
    print("Saving :", now)

    print("Valid: ", np.sum(big_logic)," Invalid :", img_data.shape[0]*img_data.shape[1]-np.sum(big_logic) )
    #img_data[0,0]=0
    #img.FlushCache()

    print(gdal.GetLastErrorMsg())
    dst_ds.GetRasterBand(1).WriteArray(dst_data)
    dst_ds.GetRasterBand(1).FlushCache()
    dst_ds.FlushCache()
    dst_ds.GetRasterBand(1).SetNoDataValue(65535)
    #dst_ds.close()
    print(gdal.GetLastErrorMsg())
    #print(dst_data)
    if saveJ2K:
        now = datetime.datetime.now()
        print("Saving J2K: ",now)
        driver = gdal.GetDriverByName("JP2OpenJPEG")
        dst_ds = driver.CreateCopy(destFile+".jp2", dst_ds, strict=0)
        dst_ds=None

    now = datetime.datetime.now()
    print("Finished: ",now)


from glob import glob
import os
import sys

starting_path="/home/mquinteiro/Downloads/"
starting_path=""
writeJP2=False
rewrite=False
for i in range(0,len(sys.argv)):
    if (sys.argv[i] == '-p'):
        starting_path=sys.argv[i+1]
        i+=1
    elif sys.argv[i] == "-j" :
        writeJP2=True
    elif sys.argv[i] == "-r" :
        rewrite=True

products = glob(starting_path+"*_MSIL2A_*")
for product in products:
    if os.path.isdir(product):
        tiles = glob(product+"/GRANULE/*L2A_*")
        for tile in tiles:
            if os.path.isdir(tile):
                scl_files=glob(tile+"/IMG_DATA/*_SCL*_20m.jp2")
                if scl_files.__len__() == 0:
                    scl_files=glob(tile+"/IMG_DATA/R20m/*_SCL*_20m.jp2")
                if scl_files.__len__() == 0:
                    continue
                cld_files=glob(tile+"/QI_DATA/*_CLD*_20m.jp2")
                if cld_files.__len__() == 0:
                    cld_files=glob(tile+"/QI_DATA/R20m/*_CLD*_20m.jp2")
                if cld_files.__len__() == 0:
                    continue
                # We have  CLD and SCL so continue.
                for end10 in file_endings10:
                    imgs_files = glob(tile + "/IMG_DATA/R10m/L2A_*"+end10+"_10m.jp2")
                    if(imgs_files.__len__()==0):
                        continue
                    output_file = os.path.join(os.path.dirname(imgs_files[0]),
                           os.path.basename(imgs_files[0]).replace("L2A_","L2C_").replace(".jp2", ""))

                    #check if work is done
                    if not rewrite and os.path.isfile(output_file+".tif"):
                        continue
                    if writeJP2:
                        maskFile(imgs_files[0], cld_files[0], scl_files[0], output_file, factor=2, saveJ2K=True)
                    else:
                        maskFile(imgs_files[0],cld_files[0],scl_files[0],output_file,factor=2,saveJ2K=False)

                for end20 in file_endings20:
                    imgs_files = glob(tile + "/IMG_DATA/R20m/L2A_*" + end20 + "_20m.jp2")
                    if (imgs_files.__len__() == 0):
                        continue
                    output_file = os.path.join(os.path.dirname(imgs_files[0]),
                       os.path.basename(imgs_files[0]).replace("L2A_", "L2C_").replace(".jp2",""))
                    # check if work is done
                    if not rewrite and os.path.isfile(output_file + ".tif"):
                        continue
                    if writeJP2:
                        maskFile(imgs_files[0], cld_files[0], scl_files[0], output_file, factor=1, saveJ2K=True)
                    else:
                        maskFile(imgs_files[0],cld_files[0],scl_files[0],output_file,factor=1,saveJ2K=False)

