import re
import numpy as np
import struct
import sys

def AllIntInStr(my_string):
    arr_str = re.findall(r'\d+', my_string)
    res_int = []
    for item in arr_str:
        res_int.append(int(item))
    return res_int

def FirstIntInStr(my_string):
    arr = AllIntInStr(my_string)
    if (len(arr) > 0):
        return arr[0]
    else:
        return None

def LastIntInStr(my_string):
    arr = AllIntInStr(my_string)
    if (len(arr) > 0):
        return arr[len(arr)-1]
    else:
        return None
    
def GetFilenameFromCompletePath(my_string):
    res = None
    if len(my_string)>0:
        split1 = my_string.split('\\')
        if len(split1)>0:
            split2 = split1[-1].split('/')
            if len(split2)>0:
                res = split2[-1]
    return res

class MIhdrData:
    def __init__(self, name, depth, format, value):
        self.name = name
        self.depth = int(depth)
        self.format = format
        self.value = value

def DataType(strFormat):
    if (strFormat == 'b'):
        return np.int8
    elif (strFormat == 'B'):
        return np.uint8
    elif (strFormat == '?'):
        return bool
    elif (strFormat == 'h'):
        return np.int16
    elif (strFormat == 'H'):
        return np.uint16
    elif (strFormat == 'i'):
        return np.int32
    elif (strFormat == 'I'):
        return np.uint32
    elif (strFormat == 'f'):
        return np.float32
    elif (strFormat == 'd'):
        return np.float64
    else:
        raise ValueError('Format ' + str(strFormat) + ' not recognized!')
        
def DataDepth(strFormat):
    if (strFormat == 'b'):
        return 1
    elif (strFormat == 'B'):
        return 1
    elif (strFormat == '?'):
        return 1
    elif (strFormat == 'h'):
        return 2
    elif (strFormat == 'H'):
        return 2
    elif (strFormat == 'i'):
        return 4
    elif (strFormat == 'I'):
        return 4
    elif (strFormat == 'f'):
        return 4
    elif (strFormat == 'd'):
        return 8
    else:
        raise ValueError('Format ' + strFormat + ' not recognized!')

def defaultMIheaderBuilder(img_num=0,px_num=0):
    return MIheaderBuilder(hdr_specs=[{'key':'img_num','size':4,'type':'i','value':img_num},{'key':'px_num','size':4,'type':'i','value':px_num}])

'''
hdr_specs: list of dictionnaries, one per key
'''
def MIheaderBuilder(hdr_specs=[{'key':'img_num','size':4,'type':'i','value':0},{'key':'px_num','size':4,'type':'i','value':0}]):
    res = []
    for item in hdr_specs:
        res.append(MIhdrData(item['key'], item['size'], item['type'], item['value']))
    return res

def MIinfo(PixelFormat, imgWidth, imgHeight):
    return {
            'depth':      DataDepth(PixelFormat),
            'format':  PixelFormat,
            'img_width':      imgWidth, 
            'img_height':     imgHeight,
            'px_num': imgWidth*imgHeight
            }
def ImgsToByteArray(data, data_format, do_flatten=True):

    res = bytes()
    if do_flatten:
        data = data.flatten().astype(DataType(data_format))
    else:
        data = data.astype(DataType(data_format))
    #print('Writing ' + str(len(data)) + ' "' + str(data_format) + '" to file')
    res += struct.pack(('%s' + data_format) % len(data), *data)

    return res
    
    
def WriteMIfile(data_arr, MIfile_name, data_format, prefix_byteString=None, returnHandle=False, bufMaxSize=None):

    if (bufMaxSize==None):
        bufMaxSize = 100000000
    
    MIfile_handle = open(MIfile_name, 'wb')
    
    if (prefix_byteString!=None):
        MIfile_handle.write(prefix_byteString)
    
    if (sys.getsizeof(data_arr) > bufMaxSize):
        if (sys.getsizeof(data_arr[0]) > bufMaxSize):
            raise IOError('WriteMIfile is trying to write a very large array. Enhanced memory control is still under development')
        else:
            n_elem_xsec = len(data_arr[0].flatten())
            xsec_per_buffer = max(1, bufMaxSize//n_elem_xsec)
            for i in range(0, len(data_arr), xsec_per_buffer):
                MIfile_handle.write(ImgsToByteArray(data_arr[i:min(i+xsec_per_buffer, len(data_arr))], data_format, do_flatten=True))
    else:
        MIfile_handle.write(ImgsToByteArray(data_arr, data_format, do_flatten=True))
        
    
    if (returnHandle):
        return MIfile_handle
    else:
        MIfile_handle.close()
        return None


def AppendToMIfile(fileHandle, data_arr, data_format):
    fileHandle.write(ImgsToByteArray(data_arr, data_format))



def OpenMIfileForWriting(MIfile_name, Header=None):
    
    MIfile_handle = open(MIfile_name, 'wb')
    if (Header!=None):
        buf = bytes()
        for elem_hdr in Header:
            buf += struct.pack(elem_hdr.format, elem_hdr.value)
        MIfile_handle.write(buf)
    return MIfile_handle


def ExportMIfile(data_arr, MIfile_name, data_format):
    
    px_num = 1
    for dim in data_arr.shape[1:]:
        px_num *= dim
    
    MIhdr = defaultMIheaderBuilder(len(data_arr), px_num)
    
    buf = bytes()
    for elem_hdr in MIhdr:
        buf += struct.pack(elem_hdr.format, elem_hdr.value)
        
    WriteMIfile(data_arr, MIfile_name, data_format, buf)

def LoadInfo_MIfile(MIfile_handle, MIheader):
    
    MIfile_handle.seek(0)
    hdr_size = 0
    
    # for each element in the header, read the corresponding number of bytes
    # and store the value in the header structure array
    for cur_element in MIheader:
    
        cur_data = MIfile_handle.read(cur_element.depth)
        cur_element.value = struct.unpack(cur_element.format, cur_data)[0]
        hdr_size += cur_element.depth
    
    return hdr_size

def ReadHeader_MIfile(MIfile_name, DetailedOutput=False):
    MIheader = defaultMIheaderBuilder()
    #for data in MIheader:
    #    print data.name, data.depth, data.format
    MIfile_handle = open(MIfile_name, 'rb')
    tot_hdr_size = LoadInfo_MIfile(MIfile_handle, MIheader)
    MIfile_handle.close()
    if DetailedOutput:
        return MIheader, tot_hdr_size
    else:
        return MIheader

def MIinfoFromName(MI_filename, byteFormat='B'):
    int_list = AllIntInStr(GetFilenameFromCompletePath(MI_filename))
    if (len(int_list) > 2):
        res = MIinfo(byteFormat, int(int_list[-3]), int(int_list[-2]))
        res['img_num'] = int(int_list[-1])
        return res
    elif (len(int_list) > 1):
        return  MIinfo(byteFormat, int(int_list[-2]), int(int_list[-1]))
    else:
        raise ValueError('Cannot retrieve image shape from filename ' + str(MI_filename))
        return None
 
def LoadMIfile(MIfile_name, MI_info=None, returnHeader=False):
    if (MI_info==None):
        MI_info = MIinfoFromName(MIfile_name)
    MIfile_handle = open(MIfile_name, 'rb')
    if ('hdr_size' in MI_info.keys()):
        if ('img_num' in MI_info.keys() and 'px_num' in MI_info.keys()):
            MIheader = defaultMIheaderBuilder(MI_info['img_num'], MI_info['px_num'])
        elif (MI_info['hdr_size'] == 8 and 'px_num' in MI_info.keys()):
            MIheader = defaultMIheaderBuilder(0, MI_info['px_num'])
        else:
            MIfile_handle.seek(MI_info['hdr_size'])
            MIheader = []
    else:
        MIheader = defaultMIheaderBuilder()
        MI_info['hdr_size'] = LoadInfo_MIfile(MIfile_handle, MIheader)
    for hdr_elem in MIheader:
        #print hdr_elem.name, hdr_elem.value
        MI_info[hdr_elem.name] = hdr_elem.value
    if (returnHeader):
        return MIfile_handle, MI_info
    else:
        return MIfile_handle

def ReadMIfile(MIfile_name, MI_info=None, Step=-1, closeAfter=True, zRange=None):
    MIfile_handle, MI_info = LoadMIfile(MIfile_name, MI_info, returnHeader=True)
    if zRange==None:
        zRange = [0, -1]
    else:
        if (len(zRange) > 2):
            if (Step > 0):
                if (Step != zRange[2]):
                    raise ValueError('ReadMIfile error: inconsistent input: Step==' + str(Step) + '; zRange==' + str(zRange))
            else:
                Step = zRange[2]
    res_3D = ReadMIfile_handle(MIfile_handle, MI_info, StartIndex=int(zRange[0]), EndIndex=int(zRange[1]), Step=Step)
    if closeAfter:
        MIfile_handle.close()
    return res_3D

def ReadMIfile_handle(MI_handle, MI_info, StartIndex=0, EndIndex=-1, Step=-1, flatten_image=False):
    if (EndIndex < 0):
        EndIndex = MI_info['img_num']
    if (Step > 1):
        res_3D = []
        for img_idx in range(StartIndex, EndIndex, Step):
            res_3D.append(getSingleImage_MIfile(MI_handle, MI_info, img_idx, flatten_image=flatten_image))
        res_3D = np.asarray(res_3D)
    else:
        res_3D = getStack_MIfile(MI_handle, MI_info, start_idx=StartIndex, imgs_num=EndIndex-StartIndex, flatten_image=flatten_image)
    return res_3D

def getSingleImage_MIfile(MIfile_handle, MIfile_info, image_idx, flatten_image=False):
    return getStack_MIfile(MIfile_handle, MIfile_info, start_idx=image_idx, imgs_num=1, flatten_image=flatten_image)[0]
    

def getROIlineStack_MIfile(MIfile_handle, MI_info, ImgRange, ROIsize, ROIline_idx=0):
    
    if (ImgRange==None):
        ImgRange = [0, -1]
    if (ImgRange[1]==-1):
        ImgRange[1] = MI_info['img_num']
    if (len(ImgRange)<3):
        ImgRange.append(1)
    
    # Checking for errors in starting position (in bytes):
    if (ImgRange[0] < 0):
        raise IOError('MI file read error: starting image index (' + str(ImgRange[0]) + ') cannot be negative')
    if (ImgRange[1] > MI_info['img_num']):
        raise IOError('MI file read error: final image index (' + str(ImgRange[1]) +\
                    ') cannot be larger than number of images (' + str(MI_info['img_num']) + ')')
    if (ImgRange[0] >= ImgRange[1]):
        raise IOError('MI file read error: invalid image range ' + str(ImgRange))
    
    #reading the selected line and storing it in a tuple
    res4D = []
    for img_idx in range(ImgRange[0], ImgRange[1], ImgRange[2]):
        res4D.append(getROIline_MIfile(MIfile_handle, MI_info, ImgIndex=img_idx, ROIsize=ROIsize, ROIline_idx=ROIline_idx))
    res4D = np.asarray(res4D)
    # Up to now in res4D[i][j][k][l]:
    # - i is time
    # - j is ROI index
    # - k,l are row and column index of pixel in ROI
    # We swapaxes to return a 4D array res4D[i][j][k][l] in which:
    # - i is ROI index
    # - j is time
    # - k,l are row and column index of pixel in ROI
    res4D = np.swapaxes(res4D, 0, 1)
   
    return res4D


def getROIline_MIfile(MIfile_handle, MI_info, ImgIndex=0, ROIsize=None, ROIline_idx=0):
        
    if (MI_info['img_width'] % ROIsize[0] > 0):
        raise IOError('ROI line read error: Image width (' + str(MI_info['img_width']) +\
                      ') has to be a multiple of ROI width (' + str(ROIsize[0]) + ')')
    
    read_line_range = [ROIline_idx * ROIsize[1], (ROIline_idx+1) * ROIsize[1]]
    
    pixels_data = getLineRange_MIfile(MIfile_handle, MI_info, ImgIndex=ImgIndex, LineRange=read_line_range, flatten=True)

    # Returns a 3D array whose components are [ROI_idx, y_in_ROI, x_in_ROI]
    ROI_per_line = int(MI_info['img_width'] // ROIsize[0])
    data_resh = pixels_data.reshape([ROIsize[1], ROI_per_line, ROIsize[0]])
    # By now, in data_resh[i][j][k]:
    # - i is the pixel row in the ROI
    # - j is the ROI index
    # - k is the pixel column in the ROI
    # We swap axes such that we return a 3D array data_resh[i][j][k] in which:
    # - i is the ROI index
    # - j,k are row and column indexes of pixel in ROI
    data_resh = np.swapaxes(data_resh, 0, 1)

    return data_resh

 
'''
ImgIndex : 0-based
LineRange : 2-element tuple [row_min_idx, row_max_idx]. If None, the whole image will be returned
'''
def getLineRange_MIfile(MIfile_handle, MI_info, ImgIndex=0, LineRange=None, flatten=False):
    
    if (LineRange==None):
        return getSingleImage_MIfile(MIfile_handle, MI_info, ImgIndex)
    
    #checking line number
    if (LineRange[0] < 0):
        raise IOError('MI file read error: line number index cannot be negative')
    elif (LineRange[1] <= LineRange[0]):
        raise IOError('MI file read error: invalid line number range ' + str(LineRange))
    elif (LineRange[1] > MI_info['img_height']):
        raise IOError('MI file read error: line number has to be smaller than the total number of lines (' + str(MI_info['img_height']) + ')')
    
    #caluclating position of line to be read inside file
    seek_pos = int(MI_info['hdr_size'] + ImgIndex * MI_info['px_num'] * MI_info['depth'] + LineRange[0] * MI_info['img_width'] * MI_info['depth'])

    # move reading pointer at line_pos
    MIfile_handle.seek(seek_pos)
    
    #calculating number of pixels to be read
    read_pixels = int(MI_info['img_width'] * (LineRange[1] - LineRange[0]))
    
    #number of bytes to be read is given by number of pixels times depth of each pixel
    bytes_to_read = int(read_pixels * MI_info['depth'])
    #print('ImgIndex ' + str(ImgIndex) + ', LineRange ' + str(LineRange) + ': seek ' + str(seek_pos) + '; read ' + str(read_pixels) + 'px (' + str(bytes_to_read) + 'b)')

    lineContent = MIfile_handle.read(bytes_to_read)
    
    if len(lineContent) < bytes_to_read:
        raise IOError('MI file read error: EOF encountered when reading line range ' + str(LineRange) +\
                        ' of image ' + str(ImgIndex) + ': ' + str(len(lineContent)) +\
                        ' instead of ' + str(bytes_to_read) + ' bytes returned')
        return None
         
    # get data type from the depth in bytes
    struct_format = ('%s' + MI_info['format']) % read_pixels

    # unpack data structure in a tuple (than converted into 1D array) of float32
    res_arr = np.asarray(struct.unpack(struct_format, lineContent))
    
    if (flatten):
        return res_arr
    else:
        return res_arr.reshape([LineRange[1] - LineRange[0], MI_info['img_width']])
    
    
    


def getStack_MIfile(MIfile_handle, MIfile_info, start_idx=0, imgs_num=-1, flatten_image=False):
    
    # Total pixel per image (taking into account the different channels)
    if ('px_num' in MIfile_info.keys()):
        pixels_per_image = MIfile_info['px_num']
        if (flatten_image):
            # make a copy to avoid changing the original image size
            MIfile_info = MIfile_info.copy()
            MIfile_info['img_height'] = 1
            MIfile_info['img_width'] = pixels_per_image
        else:
            if ('img_height' in MIfile_info.keys() and 'img_width' in MIfile_info.keys()):
                if (pixels_per_image != MIfile_info['img_height'] * MIfile_info['img_width']):
                    raise IOError('Number of pixels per image (' + str(pixels_per_image) + ') inconsistent with image dimensions ' +\
                                    '(' + str(MIfile_info['img_width']) + 'x' + str(MIfile_info['img_height']) + 'px)')
    else:
        pixels_per_image = MIfile_info['img_height'] * MIfile_info['img_width']
    
    # Calculate starting position (in bytes):
    if (start_idx < 0):
        raise IOError('MI file read error: starting image index cannot be negative')
    elif (start_idx >= MIfile_info['img_num']):
        raise IOError('MI file read error: starting image index (' + str(start_idx) + ') has to be smaller than the number of images (' + str(MIfile_info['img_num']) + ')')
    image_pos = MIfile_info['hdr_size'] + start_idx * pixels_per_image * MIfile_info['depth']
    
    # Total number of bytes to read (taking into account the different channels and the number of images)
    if (imgs_num > 0):
        if (imgs_num > MIfile_info['img_num'] - start_idx):
            raise IOError('MI file read error: image number too large')
    else:
        imgs_num = MIfile_info['img_num'] - start_idx

    # move reading pointer at image_pos
    MIfile_handle.seek(image_pos)
    
    # if image is complex, read 2 values per pixel, otherwise 1
    num_read_vals = imgs_num * pixels_per_image
    
    # whether complex or not, the number of bytes to read is total number of pixels times the single pixel depth
    bytes_to_read = imgs_num * pixels_per_image * MIfile_info['depth']
    
    # read px_number pixel, each one represented by px_depth bytes
    fileContent = MIfile_handle.read(bytes_to_read)
    
    if len(fileContent) < bytes_to_read:
        raise IOError('MI file read error: EOF encountered when reading image stack starting from ' + str(start_idx) +\
                        ' (seek offset ' + str(image_pos) + ' bytes): ' + str(len(fileContent)) + ' instead of ' +\
                        str(bytes_to_read) + ' bytes (' + str(num_read_vals) + ' pixels) returned')
        return None
    
    # get data type from the depth in bytes
    struct_format = ('%s' + MIfile_info['format']) % num_read_vals
    
    # unpack data structure in a tuple (than converted into 1D array) of float32
    res_arr = np.asarray(struct.unpack(struct_format, fileContent))
    
    # 4D array: num_images x image_height (row number) x image_width (column number) x num_channels
    data_resh = res_arr.reshape(imgs_num, MIfile_info['img_height'], MIfile_info['img_width'])

    # return image array
    return data_resh