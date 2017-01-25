subroutine	continuum(x,wx,sx,y,nx,cont,n)

! determine the continuum with one of the following algorithms:
!	cont<= 0 -- do nothing
!	cont= 1 -- polynomial fitting
!	cont= 2 -- PEM (split each range in n pieces and divide each subarray by its mean value)
!	cont= 3	-- running mean with a width of n+1 pixels
!

use share, only: dp,nsynth,hs,winter
use booklib
use lsq
		 		 
implicit none

!input/output
integer, intent(in)     :: cont		    	!choice of algorithm
integer, intent(in)	:: n		    	!order (cont=1)
					    	!number of pieces per wavelength 
					    	!        segment (cont=2) 
					    	!boxcar width is n+1 (cont=3) 
integer, intent(in)	:: nx		    	!size for x and sx
real(dp),intent(in) 	:: x(nx),wx(nx),sx(nx)  !data, wavelengths and errors
real(dp),intent(out)    :: y(nx)            	!continuum

!locals
integer			:: p1,p2	    !dummy pixel indices
real(dp)		:: med   	    !tmp var with the array mean
integer			:: nel		    !length of a section
integer			:: j,i		    !loop index
integer			:: error	    !error code for polynomial fit
real(dp)                :: xaxis(nx)        !findgen(nx)
real(dp)		:: w(nx)	    !weights
real(dp),dimension(0:n) :: coef             !coefs. for polynomial fit


if (cont <= 0) then
  y(1:nx)=1._dp
  return
endif


!set abscissae and weights needed for polynomial fitting
if (cont == 1) then
	w(:)=0._dp
	do i=1,nx
  		xaxis(i)=i*1._dp
		if (sx(i) > 0._dp) w(i)=1._dp/sx(i)**2
	enddo
endif


do j=1,nsynth		
	
	if (abs(hs(j)%res-0._dp) > 1e-6_dp) then	!skip photometry

	  if (winter == 2) then 
		  p1=minval(minloc(wx,wx >= hs(j)%lambdamin))
		  p2=maxval(maxloc(wx,wx <= hs(j)%lambdamax))
	  else
		  p1=hs(j)%pixbegin
		  p2=hs(j)%pixend
	  endif

	  !write(*,*)'p1,p2=',p1,p2

	  nel=p2-p1+1

	  select case (cont)
		  case (1)
		    	if (n == 0) then 
			    !order 0 is just the mean
			    y(p1:p2)=sum(x(p1:p2))/(nel*1._dp)
			else
			    !fit polynomial
			    coef(:)=0.0_dp
			    call lsq_fit(xaxis(1:nel),x(p1:p2),nel,n,coef,error)
			    !call poly_fit(xaxis(1:nel),x(p1:p2),w(p1:p2),nel,n,coef,error)

			    !evaluate it
			    y(p1:p2)=coef(0)
			    do i=1,n
				y(p1:p2)=y(p1:p2)+coef(i)*xaxis(1:nel)**i
			    enddo
	  	  	endif
		  case (2)
		    call pem(x(p1:p2),nel,n,y(p1:p2))	
	  	  case (3)
	    	    call filter1(x(p1:p2),nel,n,y(p1:p2))
	  	  case default
	    		write(*,*)'ferre: ERROR'
	    		write(*,*)'-- cont must be <=0,1,2,3'
	    		write(*,*)'-- this should have been caught in load_control!'
	    		stop
	  end select
	endif
enddo

end subroutine continuum
