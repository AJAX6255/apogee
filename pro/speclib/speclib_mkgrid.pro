;
; speclib_mkgrid makes grids of synthetic spectra and stores them in output
;     FITS files. The dimensionality and size of the grid is specified in
;     an input planfile. The synthetic spectra can be generated by either
;     Turbospectrum or MOOG and are stored in HDU0. 
;     One the synthetic spectra are made, they are smoothed to requested
;     resolution in HDU1, and then continuum normalized and resampled to
;     apStar resolution for the 3 chips in HDU2, HDU3, and HDU4
;     If file already exists, then spectra are not regenerated unless
;     /clobber is specified, not resmoothed unless /resmooth is specified,
;     not renormalized unless /renorm is specified
;
pro speclib_mkgrid,planfile,clobber=clobber,resmooth=resmooth,renorm=renorm,save=save,specdir=specdir,norun=norun,split=split,highres=highres


; loop over planfiles
for iplan=0,n_elements(planfile)-1 do begin

; read planfile
aploadplan,planfile[iplan],planstr

if ~keyword_set(highres) then highres=apsetpar(planstr,'highres',9)
if tag_exist(planstr,'apred_vers') then apred_vers=planstr.apred_vers else apred_vers='t9'
if tag_exist(planstr,'telescope') then telescope=planstr.telescope else telescope='apo25m'
apsetver,vers=apred_vers,telescope=telescope

; setup to work in a local directory if we have one
dir=getenv('APOGEE_LOCALDIR') 
if dir ne '' then begin
  print,'mktemp -d '+dir+'/XXXXXX'
  spawn,'mktemp -d '+dir+'/XXXXXX',temp
  dir=temp[0]
  dir=dir+'/'
  cd,dir,current=current
endif else cd,'./',current=current
print,'dir: ', dir
$pwd

; are we doing a grid with an element dimension?
elem=0
nelem=1
undefine,linelistdir
if tag_exist(planstr,'elem') then begin
  ; set up element run
  elem=planstr.elem 
  nelem=10
  name=planstr.name+elem
  ; if we are doing windows for minigrid, load them here
  ; also create custom line list in windows
  if tag_exist(planstr,'maskdir') then begin
    speclib_wline,elem,'linelist.'+strtrim(planstr.linelist,2),planstr.maskdir,wvac=wvac
    linelistdir=dir
  endif
endif else name=planstr.name

; get synthetic spectra parameters
if tag_exist(planstr,'vacuum') then vacuum=planstr.vacuum else vacuum=0
if tag_exist(planstr,'vmicro') then if planstr.vmicro[0] gt 0 then vmicro=planstr.vmicro else vmicro=0 else vmicro=0
if tag_exist(planstr,'vmacrofit') then vmacrofit=planstr.vmacrofit else vmacrofit=0
if tag_exist(planstr,'vmacro') then vmacro=planstr.vmacro else vmacro=0
if tag_exist(planstr,'solarisotopes') then solarisotopes=planstr.solarisotopes else solarisotopes=0
if tag_exist(planstr,'kurucz') then kurucz=planstr.kurucz else kurucz=0
marcs=0 
kurucz=0
if planstr.synthcode eq 'moog' then if tag_exist(planstr,'atmos') then if planstr.atmos eq 'marcs' then marcs=1
if planstr.synthcode eq 'turbospec' then if tag_exist(planstr,'atmos') then if planstr.atmos eq 'kurucz' then kurucz=1
if tag_exist(planstr,'marcsdir') then marcsdir=planstr.marcsdir
if planstr.synthcode eq 'turbospec' then file_link,getenv('SPECLIB_DIR')+'/src/turbospec/DATA','DATA',/allow

if tag_exist(planstr,'specdir') then $
  specdir=getenv('APOGEE_SPECLIB')+'/'+planstr.specdir+'/' else $
  specdir='./'
file_mkdir,specdir
if planstr.nam gt 1 or planstr.ncm gt 1 or planstr.nnm gt 1 then $
  stop,'currently only support nam=ncm=nnm=1'

; Does file exist? If so, how many extensions?
if file_test( specdir+name+'.fits') then $
  fits_info,specdir+name+'.fits',n_ext=n_ext else n_ext=-1
if keyword_set(clobber) then n_ext=-1
if keyword_set(resmooth) then n_ext=min([n_ext,0])
if keyword_set(renorm) then n_ext=min([n_ext,1])

; if we already have model spectra, read them in and load them into specdata
if n_ext ge 0 then begin
  specdata=mrdfits(specdir+name+'.fits',0,hdr) 
  if planstr.synthcode eq 'asset' then begin
    rawwave=sxpar(hdr,'CRVAL1')+lindgen(sxpar(hdr,'NAXIS1'))*sxpar(hdr,'CDELT1')
    nspec=n_elements(wave)
  endif else begin
    nspec=nint((planstr.wrange[1]-planstr.wrange[0])/planstr.dw)+1
    rawwave=planstr.wrange[0]+lindgen(nspec)*planstr.dw
  endelse
endif else begin
  ; model number of pixels and wavelengths
  nspec=nint((planstr.wrange[1]-planstr.wrange[0])/planstr.dw)+1
  rawwave=planstr.wrange[0]+lindgen(nspec)*planstr.dw
  if nelem gt 1  then specdata=fltarr(nspec,1,1,1,nelem)  else $
  specdata=fltarr(nspec,planstr.nteff,planstr.nlogg,planstr.nmh,nelem)
endelse
; if not calculated in vacuum wavelengths, then convert wavelengths to vacuum
wave=rawwave
if vacuum eq 0 then airtovac,wave

; information for smoothing
; dummy to get output npix
if tag_exist(planstr,'lsfid') then begin
  lsf=apogee_getlsf(planstr.lsfid,planstr.waveid,planstr.lsffiber,vers=apred_vers,wave=wlsf,highres=highres)
  lsfconv,wave,specdata[*,0,0,0,0],wlsf,lsf,xm,ym,highres=highres
endif else begin
  step=(max(alog(wave))-min(alog(wave)))/n_elements(wave)
  fwhm=1.d0/planstr.resolution/step
  gconv,alog(wave),specdata[*,0,0,0,0],fwhm,xm,ym,/inter
endelse
if n_ext ge 1 then smoothdata=mrdfits(name+'.fits',1) else $
  if tag_exist(planstr,'elem') then smoothdata=fltarr(n_elements(speclib_welem(exp(xm),ym,wvac)),planstr.nteff,planstr.nlogg,planstr.nmh,nelem) else $
  smoothdata=fltarr(n_elements(ym),planstr.nteff,planstr.nlogg,planstr.nmh,nelem)

; do we have a rotation dimension? If so, make the rotation kernels
if tag_exist(planstr,'nrot') then nrot=planstr.nrot else nrot=1
if tag_exist(planstr,'eps') then eps=planstr.eps else eps=0.25
if nrot gt 1 then begin
  dv=(xm[1]-xm[0])*3.e5
  for irot=0,nrot-1 do begin
    rot=planstr.rot0+irot*planstr.drot
    vrot=10^rot
    if tag_exist(planstr,'kernel') then ktype = planstr.kernel else ktype = 'rot'
    ; use either gaussian or rotation kernel, as requested
    if ktype eq 'gauss' then $
      kernel = gaussian_function(vrot/2.354/dv) $
    else if ktype eq 'rot' then $
      kernel=lsf_rotate(dv,vrot,eps=eps) $
    else stop,'unknown rotation kernel'
    kernel=kernel/total(kernel)
    tag='rot'+string(format='(i2.2)',irot)
    if irot eq 0 then begin
      type=string(n_elements(kernel),format='(i2.2)')+'f'
      create_struct,rotstr,'',tag,type
      rotstr.(irot)=kernel
    endif else add_tag,rotstr,tag,kernel,rotstr
  endfor
  print, 'Using kernel type: ', ktype
endif  else ktype='none'

; information for continuum normalization and final sampling
dx=6.d-6
;xmin=[4.180932d0,4.200888d0,4.217472d0]
;xmax=[2920,2400,1894]*dx+xmin
;xmin=[4.180704d0,4.200714d0,4.217226d0]
;xmax=[2958,2429,1935]*dx+xmin
xmin=[4.180476d0,4.200510d0,4.217064d0]
xmax=[3028,2495,1991]*dx+xmin

ixmin=nint((xmin-xmin[0])/dx)
ixmax=nint((xmax-xmin[0])/dx)-1
npix=ixmax-ixmin+1

; full spectrum on output wavelength scale (includes gaps)
xout=xmin[0]+indgen(ixmax[2]-ixmin[0]+1)*dx
xout*=alog(10.)

if tag_exist(planstr,'elem') then begin
  ; with elem option, we will only save and output the window region, so modify npix accordingly
  dummy=xout*0.
  for i=0,2 do begin
    out=speclib_welem(exp(xout[ixmin[i]:ixmax[i]]),dummy,wvac)
    npix[i]=n_elements(out)
  endfor
endif

; make normalized arrays in separate variables, since they have different lengths
if n_ext ge 2 then normdata0=mrdfits(name+'.fits',2) else $
  normdata0=fltarr(npix[0],planstr.nteff,planstr.nlogg,planstr.nmh,nelem,nrot)
if n_ext ge 3 then normdata1=mrdfits(name+'.fits',3) else $
  normdata1=fltarr(npix[1],planstr.nteff,planstr.nlogg,planstr.nmh,nelem,nrot)
if n_ext ge 4 then normdata2=mrdfits(name+'.fits',4) else $
  normdata2=fltarr(npix[2],planstr.nteff,planstr.nlogg,planstr.nmh,nelem,nrot)
if tag_exist(planstr,'elem') then begin
  ; for minigrid with windows, we need to get normalization from regular run
  continuum0=mrdfits(current+'/'+planstr.name+'.fits',4)
  continuum1=mrdfits(current+'/'+planstr.name+'.fits',5)
  continuum2=mrdfits(current+'/'+planstr.name+'.fits',6)
endif else begin
  continuum0=normdata0*0.
  continuum1=normdata1*0.
  continuum2=normdata2*0.
endelse

;contpars=[4.,10.,0.1,3.]
if tag_exist(planstr,'precontinuum') then begin
 contpars=planstr.precontinuum
 pc0=contpars[0]
 pc1=contpars[1]
 pc2=contpars[2]
 pc3=contpars[3]
endif
contpars=planstr.continuum
c0=contpars[0]
c1=contpars[1]
c2=contpars[2]
c3=contpars[3]

; loop over all of the models!
first=1
for iam=0,planstr.nam-1 do begin
  am=planstr.am0+iam*planstr.dam
  for icm=0,planstr.ncm-1 do begin
    cm=planstr.cm0+icm*planstr.dcm
    for inm=0,planstr.nnm-1 do begin
      nm=planstr.nm0+inm*planstr.dnm
      for imh=0,planstr.nmh-1 do begin
        mh=planstr.mh0+imh*planstr.dmh
        for ilogg=0,planstr.nlogg-1 do begin
          logg=planstr.logg0+ilogg*planstr.dlogg
          if logg lt 0 then loggfit=0 else if logg gt 4.5 then loggfit=4.5 else loggfit=logg
          for iteff=0,planstr.nteff-1 do begin
            teff=planstr.teff0+iteff*planstr.dteff
            nrep=0
            print,'Spectrum ...',teff,logg,mh,am,cm,nm,ktype
            if n_ext lt 0 then begin
              if n_elements(vmicro) eq 7 then $
               vout=vmicro[0]+vmicro[1]*cm+vmicro[2]*nm+vmicro[3]*am+$
                              vmicro[4]*mh+vmicro[5]*loggfit+vmicro[6]*teff $
              else if n_elements(vmicro) eq 4 then $
               vout=10.^(vmicro[0]+vmicro[1]*loggfit+vmicro[2]*loggfit^2+vmicro[3]*loggfit^3) $
              else if n_elements(vmicro) eq 1 then $
               vout=vmicro $
              else stop,'unrecognized number of vmicro elements'
              if vout lt 0.51 then vout = 0.51
              print,'calculating spectra...',teff,logg,mh,am,cm,nm,vout,ktype
              if planstr.synthcode eq 'turbospec' then begin
               ; if synthesis fails, we try again, removing atmospheric layers
               nskip=0 
               if keyword_set(kurucz) then dskip=1 else dskip=2
               while nskip ge 0 and nskip lt 10 do begin
                 spec=speclib_mkturbospec(teff,logg,mh,am,cm,nm,$
                    wrange=planstr.wrange,dw=planstr.dw,marcsdir=marcsdir,$
                    elem=elem,linedir=linelistdir,linelist=planstr.linelist,vmicro=vout,$
                    solarisotopes=solarisotopes,specdir=specdir,$
                    nskip=nskip,kurucz=kurucz,norun=norun,save=save,split=split) 
	         if n_elements(spec) eq 1 then nskip+=dskip else nskip=-1
               endwhile
               ; if synthesis still fails, then we try again with adjacent models
               ;   aka hole-filling as done for atmosphere models
               ; NOTE: speclib_replace doesn't work if we are only doing one C,N,alpha
               ;if n_elements(spec) eq 1 then begin
               ;  nrep=1 & nskip=0
               ;  while n_elements(spec) eq 1 and nrep lt 25 do begin
               ;    rep=speclib_replace(imh,planstr.nmh,icm,planstr.ncm,inm,planstr.nnm,iam,planstr.nam,nrep=nrep)
               ;    spec=speclib_mkturbospec(teff,logg,rep[0],rep[3],rep[1],rep[2],$
               ;     wrange=planstr.wrange,dw=planstr.dw,width=planstr.width,$
               ;     elem=elem,linelist=planstr.linelist,vmicro=vout,$
               ;     solarisotopes=solarisotopes,save=save,specdir=specdir,$
               ;     nskip=nskip) 
               ;    nrep+=1
               ;  endwhile
               ;  if n_elements(spec) eq 1 then stop,'halt: no replacement model found',mh,am,cm,nm
               ;endif
              endif else $
              spec=speclib_mkmoog(teff,logg,mh,am,cm,nm,wrange=planstr.wrange,$
                    dw=planstr.dw,width=planstr.width,elem=elem,$
                    linelist=planstr.linelist,vmicro=vout,$
                    solarisotopes=solarisotopes,save=save,marcs=marcs)
              ; load spectrum into specdata array
              if nelem gt 1 then specdata[*,0,0,0,*]=spec else $
              specdata[*,iteff,ilogg,imh,*]=spec
              ; load back into spec in case of failed synthesis
              if nelem gt 1 then spec=reform(specdata[*,0,0,0,*]) else $
              spec=reform(specdata[*,iteff,ilogg,imh,*])
            endif else spec=reform(specdata[*,iteff,ilogg,imh,*])
            if min(spec) eq 0 and max(spec) eq 0 then begin
              print,'bad spectrum: ', iteff, ilogg, imh
              bad=1
            endif else bad=0
            if ~keyword_set(norun) and  n_ext lt 1 then begin
              smooth=[]
              for ielem=0,nelem-1 do begin
                print,'smoothing spectra...',ielem,nelem
                if tag_exist(planstr,'lsfid') then begin
                  lsfconv,wave,spec[*,ielem],wlsf,lsf,xm,ym,highres=highres
                endif else begin
                  gconv,alog(wave),spec[*,ielem],fwhm,xm,ym,/inter
                endelse
                if vmacrofit gt 0 then begin
                  if n_elements(vmacro) eq 4 then $
                    vm=10.^(vmacro[0]+vmacro[1]*alog10(teff)+vmacro[2]*logg+vmacro[3]*mh) $
                  else if n_elements(macro) eq 1 then vm=vmacro else stop,'unrecognized number of vmacro elements'
                  if vm gt 15. then vm=15.
                  print, 'Using vmacro: ', vm
                  dv=(xm[1]-xm[0])*3.e5
                  sigvmacro=vm/2.354/dv
                  smooth=[[smooth],[gauss_smooth(ym,sigvmacro)]]
                endif else smooth=[[smooth],[ym]]
                ; if this is a filled hole, set first element to negative to flag for later marking as hole
                if nrep gt 0 then smooth[0,ielem]=-1.*ym[0]
              endfor
            endif
            if ~keyword_set(norun) and n_ext lt 2 then begin
              print,'normalizing spectra...'
              for ielem=0,nelem-1 do begin
               for irot=0,nrot-1 do begin
                if nrot gt 1 then begin
                 if n_elements(rotstr.(irot)) gt 1 then $
                  rspec=convol(smooth[*,ielem],rotstr.(irot)) else $
                  rspec=smooth[*,ielem]
                endif else rspec=smooth[*,ielem]
                yout=interpol(rspec,xm,xout,/spl)
                ; do continuum normalization in chunks
                if tag_exist(planstr,'precontinuum') then begin
                  for jchip=0,2 do begin
                    speclib_continuum,pc0,pc1,pc2,pc3,yout[ixmin[jchip]:ixmax[jchip]],yout_cont
                    yout[ixmin[jchip]:ixmax[jchip]]/=yout_cont
                  endfor
                endif
                if bad then begin
                  smoothdata[*,iteff,ilogg,imh,ielem]=0.
	          normdata0[*,iteff,ilogg,imh,ielem,irot]=0.
	          normdata1[*,iteff,ilogg,imh,ielem,irot]=0.
	          normdata2[*,iteff,ilogg,imh,ielem,irot]=0.
                endif else begin
                  if tag_exist(planstr,'elem') then begin
                    ; with elem option, we will only save and output the window region
                    out=speclib_welem(exp(xm),smooth[*,ielem],wvac)
                    smoothdata[*,iteff,ilogg,imh,ielem]=out
	            norm=yout[ixmin[0]:ixmax[0]]/continuum0[*,iteff,ilogg,imh,0,irot]
                    out=speclib_welem(exp(xout[ixmin[0]:ixmax[0]]),norm,wvac)
	            normdata0[*,iteff,ilogg,imh,ielem,irot]=out
	            norm=yout[ixmin[1]:ixmax[1]]/continuum1[*,iteff,ilogg,imh,0,irot]
                    out=speclib_welem(exp(xout[ixmin[1]:ixmax[1]]),norm,wvac)
	            normdata1[*,iteff,ilogg,imh,ielem,irot]=out
	            norm=yout[ixmin[2]:ixmax[2]]/continuum2[*,iteff,ilogg,imh,0,irot]
                    out=speclib_welem(exp(xout[ixmin[2]:ixmax[2]]),norm,wvac)
	            normdata2[*,iteff,ilogg,imh,ielem,irot]=out
                  endif else begin
                    smoothdata[*,iteff,ilogg,imh,ielem]=smooth[*,ielem]
                    speclib_continuum,c0,c1,c2,c3,yout[ixmin[0]:ixmax[0]],yout_cont
	            normdata0[*,iteff,ilogg,imh,ielem,irot]=yout[ixmin[0]:ixmax[0]]/yout_cont
	            continuum0[*,iteff,ilogg,imh,ielem,irot]=yout_cont
                    speclib_continuum,c0,c1,c2,c3,yout[ixmin[1]:ixmax[1]],yout_cont
	            normdata1[*,iteff,ilogg,imh,ielem,irot]=yout[ixmin[1]:ixmax[1]]/yout_cont
	            continuum1[*,iteff,ilogg,imh,ielem,irot]=yout_cont
                    speclib_continuum,c0,c1,c2,c3,yout[ixmin[2]:ixmax[2]],yout_cont
	            normdata2[*,iteff,ilogg,imh,ielem,irot]=yout[ixmin[2]:ixmax[2]]/yout_cont
	            continuum2[*,iteff,ilogg,imh,ielem,irot]=yout_cont
                  endelse
                endelse
;junk=where(finite(normdata0) eq 0,nbad)
;if nbad gt 0 then stop,'0 non finite ', iteff, ilogg, imh, ielem
;junk=where(finite(normdata1) eq 0,nbad)
;if nbad gt 0 then stop,'1 non finite ', iteff, ilogg, imh, ielem
;junk=where(finite(normdata2) eq 0,nbad)
;if nbad gt 0 then stop,'2 non finite ', iteff, ilogg, imh, ielem
               endfor
              endfor
            endif
	    first=0
          endfor
        endfor
      endfor
    endfor
  endfor
endfor

; output FITS file
if getenv('APOGEE_LOCALDIR') ne '' then cd,current

; first write raw model spectra
sxaddpar,shdr,'CTYPE1','WAVELENGTH'
sxaddpar,shdr,'CRVAL1',rawwave[0]
sxaddpar,shdr,'CRPIX1',1
sxaddpar,shdr,'CDELT1',rawwave[1]-rawwave[0]
sxaddpar,shdr,'LOGW',0
if tag_exist(planstr,'width') then sxaddpar,shdr,'WIDTH',planstr.width
if tag_exist(planstr,'linelist') then sxaddpar,shdr,'LINELIST',planstr.linelist
idim=2
if planstr.nteff gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'TEFF'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.teff0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dteff
  idim+=1
endif else sxaddpar,shdr,'TEFF',planstr.teff0
if planstr.nlogg gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'LOGG'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.logg0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dlogg
  idim+=1
endif else sxaddpar,shdr,'LOGG',planstr.logg0
if planstr.nmh gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'M_H'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.mh0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dmh
  idim+=1
endif else sxaddpar,shdr,'M_H',planstr.mh0
if planstr.nam gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'ALPHA_M'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.am0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dam
  idim+=1
endif else sxaddpar,shdr,'ALPHA_M',planstr.am0
if planstr.ncm gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'C_M'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.cm0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dcm
  idim+=1
endif else sxaddpar,shdr,'C_M',planstr.cm0
if planstr.nnm gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'N_M'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.nm0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.dnm
  idim+=1
endif else sxaddpar,shdr,'N_M',planstr.nm0
if nelem gt 1 or nrot gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),elem
  idim+=1
endif
if planstr.synthcode eq 'asset' then $
sxaddpar,shdr,'COMMENT','ASSET generated synthetic spectra' else $
if planstr.synthcode eq 'turbospec' then $
sxaddpar,shdr,'COMMENT','TURBOSPEC generated synthetic spectra' else $
if planstr.synthcode eq 'moog' then $
sxaddpar,shdr,'COMMENT','MOOG generated synthetic spectra' else $
sxaddpar,shdr,'COMMENT','unknown source generated synthetic spectra'
mkhdr,hdr,specdata
for ihdr=0,n_elements(shdr)-1 do begin
  card=strmid(shdr[ihdr],0,8)
  if card ne '' then sxaddpar,hdr,card,sxpar(shdr,card)
endfor
sxaddpar,hdr,'VERS',getenv('APOGEE_VER'),'SPECLIB Version'
if n_ext lt 0 and nelem eq 1 then mwrfits,specdata,specdir+name+'.fits',hdr,/create

; smoothed data
sxaddpar,shdr,'CRVAL1',xm[0]
sxaddpar,shdr,'CRPIX1',1
sxaddpar,shdr,'CDELT1',xm[1]-xm[0]
sxaddpar,shdr,'LOGW',2
sxaddpar,shdr,'RESOLUTI',planstr.resolution
mkhdr,hdr,smoothdata
for ihdr=0,n_elements(shdr)-1 do begin
  card=strmid(shdr[ihdr],0,8)
  if card ne '' and strmid(card,0,4) ne 'END ' then sxaddpar,hdr,card,sxpar(shdr,card)
endfor
sxaddpar,hdr,'COMMENT','VMACRO: '+string(vmacro,format='(8f8.2)')
sxaddpar,hdr,'COMMENT','VMICRO: '+string(vmicro,format='(8f8.2)')
sxaddpar,hdr,'VERS',getenv('APOGEE_VER'),'SPECLIB Version'
mwrfits,smoothdata,name+'.fits',hdr,/create

; normalized data  (separate chunks)
sxaddpar,shdr,'CRVAL1',xmin[0]
sxaddpar,shdr,'CRPIX1',1
sxaddpar,shdr,'CDELT1',dx
sxaddpar,shdr,'LOGW',1
sxaddpar,shdr,'ORDER',contpars[0]
sxaddpar,shdr,'NITER',contpars[1]
sxaddpar,shdr,'LOWREJ',contpars[2]
sxaddpar,shdr,'HIGHREJ',contpars[3]
if nrot gt 1 then begin
  sxaddpar,shdr,'CTYPE'+string(format='(i1)',idim),'LGVSINI'
  sxaddpar,shdr,'CRVAL'+string(format='(i1)',idim),planstr.rot0
  sxaddpar,shdr,'CRPIX'+string(format='(i1)',idim),1
  sxaddpar,shdr,'CDELT'+string(format='(i1)',idim),planstr.drot
  idim+=1
endif

; write out normalized spectra
for ichip=0,2 do begin
  if ichip eq 0 then data=normdata0 else if ichip eq 1 then data=normdata1 else data=normdata2
  mkhdr,hdr,data,/image
  sxaddpar,shdr,'CRVAL1',xmin[ichip]
  for ihdr=0,n_elements(shdr)-1 do begin
    card=strmid(shdr[ihdr],0,8)
    if card ne '' and strmid(card,0,4) ne 'END ' then sxaddpar,hdr,card,sxpar(shdr,card)
  endfor
  mwrfits,data,name+'.fits',hdr
endfor
; write out continuum normalization
if ~tag_exist(planstr,'elem') then begin
 for ichip=0,2 do begin
  if ichip eq 0 then data=continuum0 else if ichip eq 1 then data=continuum1 else data=continuum2
  mkhdr,hdr,data,/image
  sxaddpar,shdr,'CRVAL1',xmin[ichip]
  for ihdr=0,n_elements(shdr)-1 do begin
    card=strmid(shdr[ihdr],0,8)
    if card ne '' and strmid(card,0,4) ne 'END ' then sxaddpar,hdr,card,sxpar(shdr,card)
  endfor
  mwrfits,data,name+'.fits',hdr
 endfor
endif
; compress using gzip fpack (lossless)
file_delete,name+'.fits.fz',/allow
spawn,['fpack','-g','-D','-Y',name+'.fits'],/noshell

endfor  ; loop over planfiles
end