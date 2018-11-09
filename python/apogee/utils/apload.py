# encoding: utf-8
#
# @Author: Jon Holtzman
# @Date: March 2018
# @Filename: synth.py
# @License: BSD 3-Clause
# @Copyright: Jon Holtzman

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from astropy.io import fits
import os
from sdss_access.path import path
from sdss_access.sync.http import HttpAccess
import pdb
import sys

class ApLoad :

    def __init__(self,dr=None,apred='r8',apstar='stars',aspcap='l31c',results='l31c.2',telescope='apo25m',instrument='apogee-n',verbose=False) :
        self.apred=apred
        self.apstar=apstar
        self.aspcap=aspcap
        self.results=results
        self.telescope=telescope
        self.instrument=instrument
        self.verbose=verbose
        if dr == 'dr10' : self.dr10()
        elif dr == 'dr12' : self.dr12()
        elif dr == 'dr13' : self.dr13()
        elif dr == 'dr14' : self.dr14()
        # set up 
        self.sdss_path=path.Path()
        self.http_access=HttpAccess(verbose=verbose)
        self.http_access.remote()
   
    def settelescope(self,telescope) :
        self.telescope=telescope
        if 'apo' in telescope : self.instrument='apogee-n'
        if 'lco' in telescope : self.instrument='apogee-s'
 
    def setinst(self,instrument) :
        self.instrument=instrument
 
    def dr10(self) :
        self.apred='r3'
        self.apstar='s3'
        self.aspcap='v304'
        self.results='v304'

    def dr12(self) :
        self.apred='r5'
        self.aspcap='l25_6d'
        self.results='v603'

    def dr13(self) :
        self.apred='r6'
        self.aspcap='l30e'
        self.results='l30e.2'

    def dr14(self) :
        self.apred='r8'
        self.aspcap='l31c'
        self.results='l31c.2'

    def printerror(self) :
        print('cannot find file: do you have correct version? permission? wget authentication?')

    def allStar(self,hdu=None) :
        ''' Read allStar file (downloading if necesssary)'''
        file = self.allfile('allStar')
        try :
            file = self.allfile('allStar')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()

    def allVisit(self,hdu=None) :
        ''' Read allVisit file (downloading if necesssary)'''
        try :
            file = self.allfile('allVisit')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()
    
    def allPlates(self,hdu=None) :
        ''' Read allPlates file (downloading if necesssary)'''
        try :
            file = self.allfile('allPlates')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()
    
    def allExp(self,hdu=None) :
        ''' Read allExp file (downloading if necesssary)'''
        try :
            file = self.allfile('allExp')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()
    
    def allSci(self,hdu=None) :
        ''' Read allSci file (downloading if necesssary)'''
        try :
            file = self.allfile('allSci')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()
    
    def allCal(self,hdu=None) :
        ''' Read allCal file (downloading if necesssary)'''
        try :
            file = self.allfile('allCal')
            return self._readhdu(file,hdu=hdu)
        except :
            self.printerror()
    
    def apR(self,*args,**kwargs) :
        """
        NAME: apload.apR
        PURPOSE:  read apR file (downloading if necessary)
        USAGE:  ret = apload.apR(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apR(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'R',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'R',**kwargs)
            except :
                self.printerror()
    
    def apFlat(self,*args,**kwargs) :
        """
        NAME: apload.apFlat
        PURPOSE:  read apFlat file (downloading if necessary)
        USAGE:  ret = apload.apFlat(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apFlat(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'Flat',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'Flat',**kwargs)
            except :
                self.printerror()
    
    def apWave(self,*args,**kwargs) :
        """
        NAME: apload.apWave
        PURPOSE:  read apWave file (downloading if necessary)
        USAGE:  ret = apload.apWave(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apWave(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'Wave',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'Wave',**kwargs)
            except :
                self.printerror()
    
    def apLSF(self,*args,**kwargs) :
        """
        NAME: apload.apLSF
        PURPOSE:  read apLSF file (downloading if necessary)
        USAGE:  ret = apload.apLSF(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apLSF(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'LSF',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'LSF',**kwargs)
            except :
                self.printerror()
    
    def apPSF(self,*args,**kwargs) :
        """
        NAME: apload.apPSF
        PURPOSE:  read apPSF file (downloading if necessary)
        USAGE:  ret = apload.apPSF(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apPSF(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'PSF',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'PSF',**kwargs)
            except :
                self.printerror()
    
    def apEPSF(self,*args,**kwargs) :
        """
        NAME: apload.apEPSF
        PURPOSE:  read apEPSF file (downloading if necessary)
        USAGE:  ret = apload.apEPSF(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: apEPSF(imagenumber)')
        else :
            try :
                file = self.allfile(
                   'EPSF',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'EPSF',**kwargs)
            except :
                self.printerror()
    
    def ap1D(self,*args,**kwargs) :
        """
        NAME: apload.ap1D
        PURPOSE:  read ap1D file (downloading if necessary)
        USAGE:  ret = apload.ap1D(imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: ap1D(imagenumber)')
        else :
            try :
                file = self.allfile(
                   '1D',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'1D',**kwargs)
            except :
                self.printerror()
    
    
    def ap2D(self,*args,**kwargs) :
        """
        NAME: apload.ap2D
        PURPOSE:  read ap2D file (downloading if necessary)
        USAGE:  ret = apload.ap2D(imagenumber)
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        fz=''
        for key in kwargs : 
            if key == 'fz' : fz='fz'
        if len(args) != 1 :
            print('Usage: ap2D(imagenumber)')
        else :
            try :
                file = self.allfile(
                   '2D'+fz,num=args[0],mjd=self.cmjd(args[0]),chips=True)
                print('file: ', file)
                return self._readchip(file,'2D',**kwargs)
            except :
                self.printerror()
    
    def ap2Dmodel(self,*args,**kwargs) :
        """
        NAME: apload.ap2Dmodel
        PURPOSE:  read ap2Dmodel file (downloading if necessary)
        USAGE:  ret = apload.ap2Dmodel(imagenumber)
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 1 :
            print('Usage: ap2Dmodel(imagenumber)')
        else :
            try :
                file = self.allfile(
                   '2Dmodel',num=args[0],mjd=self.cmjd(args[0]),chips=True)
                return self._readchip(file,'2Dmodel',**kwargs)
            except :
                self.printerror()
    
    def apCframe(self,*args, **kwargs) :
        """
        NAME: apload.apCframe
        PURPOSE:  read apCframe file (downloading if necessary)
        USAGE:  ret = apload.apCframe(plate,mjd,imagenumber[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 4 :
            print('Usage: apCframe(field,plate,mjd,imagenumber)')
        else :
            try :
                file = self.allfile(
                   'Cframe',field=args[0],plate=args[1],mjd=args[2],num=args[3],chips=True)
                return self._readchip(file,'Cframe',**kwargs)
            except :
                self.printerror()
    
    def apPlate(self,*args, **kwargs) :
        """
        NAME: apload.apPlate
        PURPOSE:  read apPlate file (downloading if necessary)
        USAGE:  ret = apload.ap2D(plate,mjd[,hdu=N,tuple=True])
        RETURNS: if hdu==None : dictionary of ImageHDUs (all extensions) 
                                for chips 'a', 'b', 'c'
                 if hdu=N : returns dictionaries (data, header) for specified HDU
                 if tuple=True : returns tuples rather than dictionaries
        """
        if len(args) != 2 :
            print('Usage: apPlate(plate,mjd)')
        else :
            try :
                file = self.allfile(
                   'Plate',plate=args[0],mjd=args[1],chips=True)
                return self.self._readchip(file,'Plate',**kwargs)
            except :
                self.printerror()
    
    def apVisit(self,*args, **kwargs) :
        """
        NAME: apload.apVisit
        PURPOSE:  read apVisit file (downloading if necessary)
        USAGE:  ret = apload.apVisit(plate,mjd,fiber,[hdu=N])
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 3 :
            print('Usage: apVisit(plate,mjd,fiber)')
        else :
            try :
                file = self.allfile(
                   'Visit',plate=args[0],mjd=args[1],fiber=args[2])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def apVisit1m(self,*args, **kwargs) :
        """
        NAME: apload.apVisit
        PURPOSE:  read apVisit file (downloading if necessary)
        USAGE:  ret = apload.apVisit(program,mjd,object,[hdu=N])
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 3 :
            print('Usage: apVisit1m(program,mjd,object)')
        else :
            try :
                file = self.allfile(
                   'Visit1m',plate=args[0],mjd=args[1],obj=args[2],telescope='apo1m')
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def apVisitSum(self,*args, **kwargs) :
        """
        NAME: apload.apVisitSum
        PURPOSE:  read apVisitSum file (downloading if necessary)
        USAGE:  ret = apload.apVisitSum(location,plate,mjd)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 3 :
            print('Usage: apVisitSum(location,plate,mjd)')
        else :
            try :
                file = self.allfile(
                   'VisitSum',location=args[0],plate=args[1],mjd=args[2])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def apStar(self,*args, **kwargs) :
        """
        NAME: apload.apStar
        PURPOSE:  read apStar file (downloading if necessary)
        USAGE:  ret = apload.apStar(field,object)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 2 :
            print('Usage: apStar(field,object)')
        else :
            try :
                file = self.allfile(
                   'Star',field=args[0],obj=args[1])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def apStar1m(self,*args, **kwargs) :
        """
        NAME: apload.apStar1m
        PURPOSE:  read apStar file (downloading if necessary)
        USAGE:  ret = apload.apStar1m(location,object)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 2 :
            print('Usage: apStar(location,object)')
        else :
            try :
                file = self.allfile(
                   'Star',location=args[0],obj=args[1],telescope='apo1m')
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def aspcapStar(self,*args, **kwargs) :
        """
        NAME: apload.aspcapStar
        PURPOSE:  read aspcapStar file (downloading if necessary)
        USAGE:  ret = apload.aspcapStar(location,object)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 2 :
            print('Usage: aspcapStar(location,object)')
        else :
            try :
                file = self.allfile(
                   'aspcapStar',location=args[0],obj=args[1])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def apField(self,*args, **kwargs) :
        """
        NAME: apload.apField
        PURPOSE:  read apField file (downloading if necessary)
        USAGE:  ret = apload.apField(field)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 1 :
            print('Usage: apField(field)')
        else :
            try :
                file = self.allfile('Field',field=args[0])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def aspcapField(self,*args, **kwargs) :
        """
        NAME: apload.aspcapField
        PURPOSE:  read aspcapField file (downloading if necessary)
        USAGE:  ret = apload.aspcapField(field)
        RETURNS: if hdu==None : ImageHDUs (all extensions)
                 if hdu=N : returns (data, header) for specified HDU
        """
        if len(args) != 1 :
            print('Usage: aspcapField(field)')
        else :
            try :
                file = self.allfile( 'aspcapField',field=args[0])
                return self._readhdu(file,**kwargs)
            except :
                self.printerror()
    
    def cmjd(self,frame) :
        """ Get chracter MJD from frame number """
        num = (frame - frame%10000 ) / 10000
        return('{:05d}'.format(int(num)+55562) )
    
    def _readchip(self,file,root,hdu=None,tuple=None,fz=None) :
        """ low level routine to read set of 3 chip files and return data as requested"""
        if self.verbose : print('Reading from file: ', file)
        try:
            if self.verbose : print (file.replace(root,root+'-a'))
            a=fits.open(file.replace(root,root+'-a'))
            if self.verbose : print (file.replace(root,root+'-b'))
            b=fits.open(file.replace(root,root+'-b'))
            if self.verbose : print (file.replace(root,root+'-c'))
            c=fits.open(file.replace(root,root+'-c'))
        except:
            print("Can't open file: ", file)
            return(0)
    
        if hdu is None :
            if tuple :
               if self.verbose : print('file: ', file,' read into tuple')
               return a,b,c 
            else :
               if self.verbose : print('file: ', file,' read into dictionary with entries a, b, c')
               return {'a' : a, 'b' : b, 'c' : c, 'filename' : file}
        else :
            a[hdu].header.set('filename',os.path.basename(file.replace(root,root+'-a')))
            b[hdu].header.set('filename',os.path.basename(file.replace(root,root+'-b')))
            c[hdu].header.set('filename',os.path.basename(file.replace(root,root+'-c')))
            if tuple :
                data =( a[hdu].data, b[hdu].data, c[hdu].data)
                header =( a[hdu].header, b[hdu].header, c[hdu].header)
            else :
                data ={'a' : a[hdu].data, 'b' : b[hdu].data, 'c': c[hdu].data}
                header = {'a' : a[hdu].header, 'b' : b[hdu].header, 'c': c[hdu].header}
            a.close()
            b.close()
            c.close()
            return data, header
    
    def _readhdu(self,file,hdu=None) :
        '''
        internal routine for reading all HDU or specified HDU and returning data and header
        '''
        if self.verbose :
            print('Reading from file: ', file)
        if hdu is None :
            fits.open(file)
            return fits.open(file)
        else :
            hd = fits.open(file)
            data = hd[hdu].data 
            header = hd[hdu].header
            hd.close()
            return data, header
    
    def filename(self,root,dr=None,apred=None,apstar=None,aspcap=None,results=None,
                 location=None,obj=None,plate=None,mjd=None,num=None,fiber=None,chips=False,field=None) :

        return self.allfile(root,dr=dr,apred=apred,apstar=apstar,aspcap=aspcap,results=results,
                            location=location,obj=obj,plate=plate,mjd=mjd,num=num,fiber=fiber,chips=chips,field=field,
                            download=False)

    def allfile(self,root,dr=None,apred=None,apstar=None,aspcap=None,results=None,
                location=None,obj=None,plate=None,mjd=None,num=None,fiber=None,chips=False,field=None,
                download=True) :
        '''
        Uses sdss_access to create filenames and download files if necessary
        '''

        if self.verbose: print('allfile...')
        if self.instrument == 'apogee-n' : prefix='ap'
        else : prefix='as'

        # get the sdss_access root file name appropriate for telescope and file 
        # usually just 'ap'+root, but not for "all" files, raw files, and 1m files, since
        # those require different directory paths
        if 'all' in root or 'aspcap' in root or 'cannon' in root :
            sdssroot = root 
        elif root == 'R' :
            if 'lco' in self.telescope: sdssroot = 'asR'
            elif 'apo1m' in self.telescope: sdssroot = 'apR-1m'
            else : sdssroot = 'apR'
        elif (self.telescope == 'apo1m' and 
           (root == 'Plan' or root == 'PlateSum' or root == 'Visit' or root == 'VisitSum' or root == 'Tellstar' or 
            root == 'Cframe' or root == 'Plate') ) :
            sdssroot = 'ap'+root+'-1m'
        else :
            sdssroot = 'ap'+root

#if n_elements(keywords) gt 0 then if tag_exist(keywords,'plate') then keywords=create_struct(keywords,'FIELD',apogee_field(0,keywords.plate))
    
        if chips == False :
            # First make sure the file doesn't exist locally
            #print(sdssroot,apred,apstar,aspcap,results,location,obj,self.telescope,field,prefix)
            filePath = self.sdss_path.full(sdssroot,
                                      apred=self.apred,apstar=self.apstar,aspcap=self.aspcap,results=self.results,
                                      field=field,location=location,obj=obj,plate=plate,mjd=mjd,num=num,
                                      telescope=self.telescope,fiber=fiber,prefix=prefix,instrument=self.instrument)
            if self.verbose: print('filePath',filePath)
            if os.path.exists(filePath) is False and download: 
                downloadPath = self.sdss_path.url(sdssroot,
                                      apred=self.apred,apstar=self.apstar,aspcap=self.aspcap,results=self.results,
                                      location=location,obj=obj,plate=plate,mjd=mjd,num=num,
                                      telescope=self.telescope,fiber=fiber,prefix=prefix,instrument=self.instrument)
                self.http_access.get(sdssroot,
                                apred=self.apred,apstar=self.apstar,aspcap=self.aspcap,results=self.results,
                                location=location,obj=obj,plate=plate,mjd=mjd,num=num,
                                telescope=self.telescope,fiber=fiber,prefix=prefix,instrument=self.instrument)
            return filePath
        else :
            for chip in ['a','b','c'] :
                #print(chip,root,num,mjd,prefix)
                filePath = self.sdss_path.full(sdssroot,
                                apred=self.apred,apstar=self.apstar,aspcap=self.aspcap,results=self.results,
                                field=field, location=location,obj=obj,plate=plate,mjd=mjd,num=num,
                                telescope=self.telescope,fiber=fiber,
                                chip=chip,prefix=prefix,instrument=self.instrument)
                if self.verbose : print('filePath: ', filePath, os.path.exists(filePath))
                if os.path.exists(filePath) is False and download : 
                  try:
                    self.http_access.get(sdssroot,
                                apred=self.apred,apstar=self.apstar,aspcap=self.aspcap,results=self.results,
                                field=field, location=location,obj=obj,plate=plate,mjd=mjd,num=num,
                                telescope=self.telescope,fiber=fiber,
                                chip=chip,prefix=prefix,instrument=self.instrument)
                  except: pdb.set_trace()
            return filePath.replace('-c','')
    
