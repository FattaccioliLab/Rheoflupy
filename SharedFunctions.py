import numpy as np
import json
import os
import re
import shutil
  
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

def AllFloatInStr(my_string):
    arr_str = re.findall(r"[-+]?\d*\.\d+|\d+", my_string)
    res_float = []
    for item in arr_str:
        res_float.append(float(item))
    return res_float

def FirstFloatInStr(my_string):
    arr = AllFloatInStr(my_string)
    if (len(arr) > 0):
        return arr[0]
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

def CheckFolderExists(folderPath):
    if (folderPath is None):
        return False
    else:
        return os.path.isdir(folderPath)


def CheckCreateFolder(folderPath):
    if (os.path.isdir(folderPath)):
        return True
    else:
        print("Created folder: {0}".format(folderPath))
        os.makedirs(folderPath)
        return False

def RemoveFolder(folderPath):
    try:
        shutil.rmtree(folderPath)
        return 0
    except:
        return 1

def CheckFileExists(filePath):
    try:
        return os.path.isfile(filePath)
    except:
        return False

def RenameFile(oldFileName, newFileName, forceOverwrite=False):
    if (CheckFileExists(oldFileName)):
        if (CheckFileExists(newFileName) and not forceOverwrite):
            raise ValueError('RenameFile error: new file name "' + str(newFileName) + '" already present on disk. Set forceOverwrite to overwrite it')
        else:
            os.rename(oldFileName, newFileName)
    else:
        raise IOError('RenameFile error: filename ' + oldFileName + ' not found.')

def DeleteFile(fileName):
    if (CheckFileExists(fileName)):
        os.remove(fileName)
    else:
        raise IOError('DeleteFile error: filename ' + fileName + ' not found.')

def GetFileSize(fileName):
    if (CheckFileExists(fileName)):
        return os.path.getsize(fileName)
    else:
        return -1

def PrintAndLog(strMsg, LogFile, addFirst="\n", flushBuffer=True):
    print(strMsg)
    if (LogFile != None):
        LogFile.write(addFirst + strMsg)
        if (flushBuffer):
            LogFile.flush()

def CastFloatListToInt(myList):
    for i in range(len(myList)):
        myList[i] = int(myList[i])
    
def FilterStringList(my_list, Prefix='', Ext='', Step=-1, FilterString='', ExcludeStrings=[], Verbose=0):
    if Verbose>0:
        print('before filter: {0} files'.format(len(my_list)))
    if (len(Prefix) > 0):
        my_list = [i for i in my_list if str(i).find(Prefix) == 0]
    if (len(Ext) > 0):
        my_list = [i for i in my_list if i[-len(Ext):] == Ext]
    if (len(FilterString) > 0):
        my_list = [i for i in my_list if FilterString in i]
    if (len(ExcludeStrings) > 0):
        for excl_str in ExcludeStrings:
            my_list = [i for i in my_list if excl_str not in i]
    if Verbose>0:
        print('after filter: {0} files'.format(len(my_list)))
    if (Step > 0):
        resList = []
        for idx in range(len(my_list)):
            if (idx % Step == 0):
                resList.append(my_list[idx])
        return resList
    else:
        return my_list
    
def FindFileNames(FolderPath, Prefix='', Ext='', Step=-1, FilterString='', ExcludeStrings=[], Verbose=0, AppendFolder=False):
    if Verbose>0:
        print('Sarching {0}{1}*{2}'.format(FolderPath, Prefix, Ext))
    FilenameList = []
    for (dirpath, dirnames, filenames) in os.walk(FolderPath):
        FilenameList.extend(filenames)
        break
    FilenameList = FilterStringList(filenames, Prefix=Prefix, Ext=Ext, Step=Step, FilterString=FilterString,\
                            ExcludeStrings=ExcludeStrings, Verbose=Verbose)
    if AppendFolder:
        for i in range(len(FilenameList)):
            FilenameList[i] = FolderPath + FilenameList[i]
    return FilenameList

"""
FirstLevelOnly: if True, only returns immediate subdirectories, otherwise returns every directory right down the tree
Returns: list with complete paths of each subdirectory
"""
def FindSubfolders(FolderPath, FirstLevelOnly=True, Prefix='', Step=-1, FilterString='', ExcludeStrings=[], Verbose=0):
    if FirstLevelOnly:
        if (Prefix == ''):
            reslist = [os.path.join(FolderPath, o) for o in os.listdir(FolderPath) if os.path.isdir(os.path.join(FolderPath,o))]
        else:
            reslist = [os.path.join(FolderPath, o) for o in os.listdir(FolderPath) if (os.path.isdir(os.path.join(FolderPath,o)) and o[:len(Prefix)]==Prefix)]
    else:
        reslist = [x[0] for x in os.walk(FolderPath)]
    return FilterStringList(reslist, Prefix='', Ext='', Step=Step, FilterString=FilterString, ExcludeStrings=ExcludeStrings, Verbose=Verbose)
    
"""
FilenameList:    list of filenames
index_pos:       index of the desired integer in the list of integer found in each string
"""
def ExtractIndexFromStrings(StringList, index_pos=0, index_notfound=-1):
    res = []
    for cur_name in StringList:
        allInts = AllIntInStr(cur_name)
        if (len(allInts) > 0):
            try:
                val = allInts[index_pos]
                res.append(val)
            except:
                res.append(index_notfound)
        else:
            res.append(index_notfound)
    return res

def ConfigGet(config, sect, key, default=None, cast_type=None, verbose=1):
    if (config.has_option(sect, key)):
        res = config[sect][key]
        if (str(res)[0] in ['[','(', '{']):
            res = json.loads(res)
        if (type(res) in [list,tuple]):
            for i in range(len(res)):
                if (type(res[i]) in [list,tuple]):
                    if (cast_type is not None):
                        for j in range(len(res[i])):
                            res[i][j] = cast_type(res[i][j])
                else:
                    if (cast_type is not None):
                        res[i] = cast_type(res[i])
                    
            return res
        else:
            if (cast_type is not None):
                if (cast_type == float and res == 'nan'):
                    return np.nan
                else:
                    return cast_type(res)
            else:
                return res
    else:
        if (verbose>0):
            print('"' + key + '" not found in section "' + sect + '": default value ' + str(default) + ' returned.')
        return default

# Boundaries: (min_val, max_val) acceptable values.
# if Boundaries != None, values outside boundaries will be discarded
def LoadIntsFromFile(FileName, Boundaries=None):
    listRes = []
    with open(FileName, "r" ) as FileData:
        for line in FileData:
            try:
                words = line.split()
                read_int = int(words[0])
                if (Boundaries == None):
                    listRes.append(read_int)
                else:
                    if (read_int > Boundaries[0] and read_int < Boundaries[1]):
                        listRes.append(read_int)
                    else:
                        print("Warning: skipped element {0} because out of boundaries".format(int(words[0])))
            except:
                pass
    return listRes

# SkipRows: number of initial header rows to be skipped (<=0 not to skip)
# Columns: list of indexes (0-based)
# if Columns != None, only colums in the list will be loaded
# Boundaries: (min_val, max_val) acceptable values.
# if Boundaries != None, values outside boundaries will be discarded
# if MaxNumRows != None, values will be loaded until the maximum row number is reached
def LoadFloatTuplesFromFile(FileName, SkipRow=-1, Columns=None, Boundaries=None, MaxNumRows=None):
    listRes = []
    line_count = 0
    with open(FileName, "r" ) as FileData:
        for line in FileData:
            line_count += 1
            if SkipRow < line_count:
                words = line.split()
                cur_tuple = []
                for word_idx in range(len(words)):
                    bln_read = True
                    if Columns != None:
                        bln_read = (word_idx in Columns)
                    if bln_read:
                        #try:
                            read_float = float(words[word_idx])
                            if (Boundaries == None):
                                cur_tuple.append(read_float)
                            else:
                                if (read_float > Boundaries[0] and read_float < Boundaries[1]):
                                    cur_tuple.append(read_float)
                                else:
                                    print("Warning: skipped element {0} because out of boundaries".format(read_float))
                        #except:
                        #    pass
                if len(cur_tuple) > 1:
                    listRes.append(cur_tuple)
                elif len(cur_tuple) == 1:
                    listRes.append(cur_tuple[0])
                if MaxNumRows != None:
                    if MaxNumRows < len(listRes):
                        break
    return listRes 