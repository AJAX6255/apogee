#
#	makefile for synspec/rotin
#	Carlos 2019
#

F90 = gfortran 
OPT= -fno-automatic 

#F90 = g95
#OPT= -fstatic -Wl,--no-relax

#F90 = sunf95
#OPT = -Bstatic -xmodel=medium 
 
#F90 =  ifort 
#OPT = -shared-intel -mcmodel medium 

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    OPT += -mcmodel=large 
endif

BINDIR=../bin

all:  compile install 

compile: s54h rotin3 list2bin

s54h: s54h.f  LINDAT.FOR  MODELP.FOR  PARAMS.FOR  SYNTHP.FOR  WINCOM.FOR
	${F90}  ${OPT} s54h.f -o s54h

rotin3: rotin3.f
	${F90}  ${OPT} rotin3.f -o rotin3

list2bin: list2bin.f
	${F90} ${OPT} list2bin.f -o list2bin

install: 
	-mkdir ${BINDIR}
	cp s54h   ${BINDIR}
	cp rotin3  ${BINDIR}
	cp list2bin  ${BINDIR}

../bin/s54h ../bin/rotin3 ../bin/list2bin: s54h rotin3 list2bin
	cp s54h   ../bin/
	cp rotin3 ../bin/
	cp list2bin ../bin/

../bin:
	mkdir ../bin
                                                        
clean: 
	rm -f s54h rotin3 list2bin ../bin/s54h ../bin/rotin3 ../bin/list2bin


