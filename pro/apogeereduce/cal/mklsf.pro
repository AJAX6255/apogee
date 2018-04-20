;======================================================================
pro mklsf,lsfid,waveid,darkid=darkid,flatid=flatid,psfid=psfid,clobber=clobber,full=full,newwave=newwave,pl=pl,fibers=fibers

  if not keyword_set(newwave) then newwave=0

  dirs=getdir(apodir,caldir,spectrodir,vers)
  caldir=dirs.caldir
  file=apogee_filename('LSF',num=lsfid[0],/nochip)
  file=file_dirname(file)+'/'+file_basename(file,'.fits')

  ; does product already exist?
  if file_test(file+'.sav') and not keyword_set(clobber) then begin
    print,' LSF file: ',file+'.sav',' already made'
    return
  endif

  ;if another process is alreadying make this file, wait!
  while file_test(file+'.lock') do apwait,file,10

  ; open .lock file
  openw,lock,/get_lun,file+'.lock'
  free_lun,lock

  cmjd=getcmjd(psfid)

  lsffile = apogee_filename('1D',num=lsfid[0],chip='c')
;  if file_test(lsffile) then begin
    mkpsf,psfid,darkid=darkid,flatid=flatid
    ;cmjd=getcmjd(lsfid)
    ;;w=approcess(lsfid,dark=darkid,flat=flatid,psf=psfid,flux=0,/clobber,/doproc)
    w=approcess(lsfid,dark=darkid,flat=flatid,psf=psfid,flux=0,wave=waveid,/doproc,/skywave)

    lsffile = file_dirname(lsffile)+'/'+string(format='(i8.8)',lsfid)
    if size(waveid,/type) eq 7 then wavefile = caldir+'wave/'+waveid else $
      wavefile = caldir+'wave/'+string(format='(i8.8)',waveid)
    psffile = caldir+'/psf/'+string(format='(i8.8)',psfid)
    print,'wavefile: ', wavefile
    aplsf,lsffile,wavefile,psf=psffile,/gauss,pl=pl
;print,'porder=2is set'
;stop
    ;if keyword_set(full) then aplsf,lsffile,wavefile,psf=psffile,newwave=newwave,/clobber
    if keyword_set(full) then aplsf,lsffile,wavefile,psf=psffile,/clobber,pl=pl,fibers=fibers ;,porder=[1,1,1,1,1,0],/pl

;,porder=2

    file_delete,file+'.lock'
;  endif else begin
;    print,'Missing ap1D file: ', lsffile
;    file_move,caldir+'lsf/'+file+'.lock',caldir+'lsf/'+file+'.missing',/overwrite
;  endelse

end
