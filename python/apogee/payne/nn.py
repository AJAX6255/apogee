from __future__ import division
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import multiprocessing as mp
from scipy.ndimage.filters import gaussian_filter
from scipy.optimize import curve_fit
from keras import models
from keras import layers
from keras import optimizers
from keras import regularizers
from astropy.io import fits
from astropy.io import ascii
from astropy.table import Table, TableColumns, Column
import pickle
import copy
import os
import sys
import pdb
import shutil
import time
from apogee.utils import apload
from apogee.aspcap import aspcap
from apogee.aspcap import norm
from tools import plots
import emcee
try: import corner
except: pass

from apogee.payne import training

nepochs=10000
nodes=20
reg=0.0005
batch_size=1000
verbose=0
reg=0.
nepochs=25000

nodes=20
nepochs=50000

nodes=300
nepochs=5

def train_pixel(file,plot=False,pixels=[1000,9000,1000],suffix='',fitfrac=1.0, order=0, threads=32,payne=False,
          teff=[0,10000],logg=[-1,6],mh=[-3,1],am=[-1,1],cm=[-2,2],nm=[-2,2],raw=False,rot=False,nolog=False,elem=False,norm=False) :
    """ Train a neural net model on an input training set
    """
    global nfit, verbose, nepochs

    # Get input spectra and parameters
    pixels=np.arange(pixels[0],pixels[1],pixels[2])
    npix=len(pixels)
    print('npix: ', npix)
    if '.npz' in file :
        a = np.load(file)
        pars = a['labels'].T
        spec = a['spectra'] 
    else :
        pars=fits.open(file+'.fits')[0].data
        if raw:
            spec=fits.open(file+'.fits')[1].data
        else :
            spec=fits.open(file+'.fits')[2].data
    head = {}
    head['nin'] = pars.shape[0]
    head['npix'] = npix

    # limit parameter range
    if payne :
        gd = np.where( (pars[:,1] > (pars[:,0]-6000.)*(1.0/1000.)+1.99) &
                       (pars[:,1] < (pars[:,0]-5000.)*(-0.45/3000.)+5.01) )[0]
    else :
        gd=np.where((pars[:,0]>=teff[0]) & (pars[:,0]<=teff[1]) &
                (pars[:,1]>=logg[0]) & (pars[:,1]<=logg[1]) &
                (pars[:,2]>=mh[0]) & (pars[:,2]<=mh[1]) &
                (pars[:,3]>=am[0]) & (pars[:,3]<=am[1]) &
                (pars[:,4]>=cm[0]) & (pars[:,4]<=cm[1])  &
                (pars[:,5]>=nm[0]) & (pars[:,5]<=nm[1]) 
               )[0]
    spec=spec[gd,:]
    pars=pars[gd,:]
    head['ntot'] = pars.shape[0]
    head['teff'] = teff
    head['logg'] = logg
    head['mh'] = mh
    head['am'] = am
    head['cm'] = cm

    # limit parameters?
    if not elem :
        if rot :
            pars=pars[:,0:8]
        else :
            pars=pars[:,0:7]

    if nolog : pars[:,2] = 10.**pars[:,2]

    #normalize spectra
    if norm :
        print('normalizing...')
        x=np.arange(0,spec.shape[1])
        specerr = np.full_like(spec[0,:],1.)
        for i in range(spec.shape[0]) :
            gd = np.where(np.isfinite(spec[i,:]))[0]
            if len(gd) == 0 :
              print(i,pars[i,:])
            if order >= 0 : 
                cont = norm.cont(spec[i,:],specerr,poly=True,order=order,chips=True)
                spec[i,:] /= cont

    if plot :
        fig,ax=plots.multi(2,2)
        plots.plotc(ax[0,0],pars[:,0],spec[:,1000],pars[:,1])
        plots.plotc(ax[1,0],pars[:,0],spec[:,1000],pars[:,2])
    print(spec.shape,pars.shape)
    shape=pars.shape

    # shuffle them and get fit and validation set
    print('shuffling...')
    p=np.random.permutation(shape[0])
    spec=spec[p,:]
    pars=pars[p,:]
    nfit=int(len(p)*fitfrac)
    shape=pars.shape

    # scale parameters to zero mean and unit standard deviation, and save scaling parameters
    pmeans=[]
    pstds=[]
    normpars = copy.copy(pars)
    for i in range(shape[1]) :
      mn=pars[:,i].mean()
      std=pars[:,i].std()
      normpars[:,i] -= mn
      if std > 0. : normpars[:,i] /= std
      pmeans.append(mn)
      pstds.append(std)

    # replot to check
    if plot :
        plots.plotc(ax[0,1],normpars[:,0],spec[:,1000],normpars[:,1])
        plots.plotc(ax[1,1],normpars[:,0],spec[:,1000],normpars[:,2])
        plt.show()

    net=models.Sequential()
    #net.add(layers.Dense(32, activation='sigmoid', input_shape=(pars.shape[1],),
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(64, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(128, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(256, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))  
    pdb.set_trace()
    net.add(layers.Dense(nodes, activation='sigmoid', input_shape=(pars.shape[1],),
            kernel_regularizer=regularizers.l2(reg)))
    net.add(layers.Dense(nodes, activation='sigmoid',kernel_regularizer=regularizers.l2(reg)))
    net.add(layers.Dense(spec.shape[1], activation='linear'))
    ##opt=optimizers.RMSprop(lr=0.01)
    opt=optimizers.Adam(lr=0.001)
    net.compile(optimizer=opt,loss='mse')
    if verbose > 0 : net.summary()

    history=net.fit(normpars[0:nfit],spec[0:nfit,:],epochs=nepochs,batch_size=batch_size,verbose=verbose,validation_data=(normpars[nfit:],spec[nfit:,:]))

    w=(net.get_weights()[0],net.get_weights()[2])
    b=(net.get_weights()[1],net.get_weights()[3])
    mod=net.predict(pars)

    print(history.history['loss'],history.history['val_loss'])

    pdb.set_trace()

    # loop over the requested pixels and normalize data to
    #   zero mean and unit standard deviation: save parameters
    weights=[]
    biases=[]
    means=[]
    stds=[]
    data=[]
    print('preparing to fit...')
    for ipix in pixels :
        pix=spec[:,ipix]
        mn=pix.mean()
        std=pix.std()
        if np.isfinite(mn) :
          pix-=mn
          pix /= std
          data.append((normpars,pix,ipix))
        means.append(mn)
        stds.append(std)

    # get the model in parallel for different pixels
    print('fitting: ',len(data))
    pool = mp.Pool(threads)
    output = pool.map_async(fit, data).get()
    pool.close()
    pool.join()
    print('done pool')

    if plot: 
        fig,ax=plots.multi(npix,7,wspace=0.001,hspace=0.001,figsize=(15,10),xtickrot=60)
        fig2,ax2=plots.multi(npix,2,wspace=0.001,hspace=0.5,figsize=(15,4),xtickrot=90)
    ifit=0
    for i,ipix in enumerate(pixels) :
      if np.isfinite(means[i]) :
        w,b,mod,loss,vloss=output[ifit]
        ifit+=1
        if plot :
              mod=mod*stds[i]+means[i]
              m=[]
              for ip in range(pars.shape[0]) : m.append(model(normpars[ip,:],means[i],stds[i],w,b)[0])
              pix=spec[:,ipix]*stds[i]+means[i]
              plots.plotc(ax[0,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,1],xr=[3000,8000],zr=[0,5])
              plots.plotc(ax[1,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,2],xr=[3000,8000],zr=[-2.0,0.75])
              plots.plotc(ax[2,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,3],xr=[3000,8000],zr=[-1,1.])
              plots.plotc(ax[3,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,4],xr=[3000,8000],zr=[-1,1.])
              plots.plotc(ax[4,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,5],xr=[3000,8000],zr=[-1,1.])
              plots.plotc(ax[5,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,6],xr=[3000,8000],zr=[0.5,3.])
              plots.plotc(ax[6,i],pars[0:nfit,0],pix[0:nfit]-mod[0:nfit,0],pars[0:nfit,7],xr=[3000,8000],zr=[0,50.])
              n=len(loss)
              plots.plotl(ax2[0,i],range(n),np.log10(loss),xr=[0,nepochs],yr=[-4,0],color='b')
              if fitfrac < 1.0 :
                  plots.plotl(ax2[0,i],range(n),np.log10(vloss),xr=[0,nepochs],yr=[-4,0],color='r')
              try : 
                  ax2[1,i].hist(np.abs(pix-mod[:,0]),bins=np.logspace(-7,3,50),histtype='step',normed=True,cumulative=True,color='k')
                  ax2[1,i].hist(np.abs(pix[0:nfit]-mod[0:nfit,0]),bins=np.logspace(-7,3,50),histtype='step',normed=True,cumulative=True,color='b')
              except: pass
              if fitfrac < 1.0 :
                  ax2[1,i].hist(np.abs(pix[nfit:]-mod[nfit:,0]),bins=np.logspace(-7,3,50),histtype='step',normed=True,cumulative=True,color='r')
              ax2[1,i].set_xlim(0,0.01)
              ax2[1,i].set_ylim(0,1.1)
              plt.draw()
              plt.show()
  
        weights.append(w)
        biases.append(b)
    if plot: fig.savefig(file+suffix+'_pixels.jpg')
    pdb.set_trace()

    # Save the model as a dictionary into a pickle file
    head['nodes'] = nodes
    head['reg'] = reg
    head['batch_size'] = batch_size
    head['nepochs'] = nepochs
    head['pmeans'] = pmeans
    head['pstds'] = pstds
    head['means'] = means
    head['stds'] = stds
    head['weights'] = weights
    head['biases'] = biases
    with open(file+suffix+'.pkl', 'w') as f:  # Python 3: open(..., 'wb')
        pickle.dump(head, f, protocol=2)
        #pickle.dump([head, pmeans, pstds, means, stds, weights, biases], f)

    return head

def fit(data) :
    """ Routine to do a single NN model fit given input data=(pars,pix)
    """
    pars=data[0]
    pix=data[1]

    showtime('fitting pixel: '+str(data[2]))

    net=models.Sequential()
    #net.add(layers.Dense(32, activation='sigmoid', input_shape=(pars.shape[1],),
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(64, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(128, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))
    #net.add(layers.Dense(256, activation='sigmoid',
    #        kernel_regularizer=regularizers.l2(reg)))
    net.add(layers.Dense(nodes, activation='sigmoid', input_shape=(pars.shape[1],),
            kernel_regularizer=regularizers.l2(reg)))
    net.add(layers.Dense(nodes, activation='sigmoid',kernel_regularizer=regularizers.l2(reg)))
    net.add(layers.Dense(1, activation='linear'))
    ##opt=optimizers.RMSprop(lr=0.01)
    opt=optimizers.Adam(lr=0.001)
    net.compile(optimizer=opt,loss='mse')
    if verbose > 0 : net.summary()

    history=net.fit(pars[0:nfit],pix[0:nfit],epochs=nepochs,batch_size=batch_size,verbose=verbose,validation_data=(pars[nfit:],pix[nfit:]))

    w=(net.get_weights()[0],net.get_weights()[2])
    b=(net.get_weights()[1],net.get_weights()[3])
    mod=net.predict(pars)

    showtime('done fitting pixel: '+str(data[2]))

    try :
        return w,b,mod,history.history['loss'],history.history['val_loss']
    except :
        return w,b,mod,history.history['loss'],0.

def merge(file,n=8) :
    """ Merge pieces of a model (e.g., run on different nodes for pixel subsets) into a single model
    """
    pm,ps,m,s,w,b=[],[],[],[],[],[]
    for i in range(n) :
      with open(file+'_{:d}.pkl'.format(i+1)) as f: 
        head = pickle.load(f)
        # pmeans, pstds same for all pixels
        m.extend(head['means'])
        s.extend(head['stds'])
        w.extend(head['weights'])
        b.extend(head['biases'])

    head['means'] = m
    head['stds'] = s
    head['weights'] = w
    head['biases'] = b
    with open(file+'.pkl', 'w') as f:  
        pickle.dump(head, f)

def sigmoid(z):
    """ sigmoid function
    """
    return 1.0/(1.0+np.exp(-z))
 
def get_model_pixel(file) :
    """ Load a model pickle file into global variables
    """
    global head, pmeans, pstds, means, stds, weights, biases, ifit

    # Getting back the objects:
    with open(file+'.pkl') as f: 
        head = pickle.load(f)
        #pmeans, pstds, means, stds, weights, biases = pickle.load(f)
    pmeans = np.array(head['pmeans'])
    pstds = np.array(head['pstds'])
    means = head['means']
    stds = head['stds']
    weights = head['weights']
    biases = head['biases']
    #pmeans = np.array(pmeans)
    #pstds = np.array(pstds)

    # get correspondence of pixel number with weight/bias index (since NaNs are not fit)
    ifit = np.zeros(len(means)).astype(int)
    j=0
    for i in range(len(means)) :
        if np.isfinite(means[i]) : 
            ifit[i] = j
            j += 1

def model_pixel(pars, mn, std, weights, biases) :
    """ function to return single pixel model given normalized input parameters and pixel normalization
    """
    return mn + std * (np.dot( sigmoid((np.dot(weights[0].T,pars)+biases[0])).T, weights[1] ) +biases[1])

def spectrum_pixel(x,*pars) :
    """ Return full spectrum given input list of pixels, parameters
    """
    spec=np.full_like(x.astype(float),np.nan)
    pnorm= (pars-pmeans)/pstds
    for j,i in enumerate(x) :
        if  np.isfinite(means[i]) :
            spec[j]= model(pnorm, means[i], stds[i], weights[ifit[i]], biases[ifit[i]]) 

    return spec

def get_model(file) :
    """ load model and set up for use
    """
    global NN_coeffs

    try :
        with open(file+'.pkl','rb') as f: 
            NN_coeffs = pickle.load(f)
    except:
        tmp = np.load(file+'.npz')
        NN_coeffs={}
        NN_coeffs['w_array_0'] = tmp["w_array_0"]
        NN_coeffs['w_array_1'] = tmp["w_array_1"]
        NN_coeffs['w_array_2'] = tmp["w_array_2"]
        NN_coeffs['b_array_0'] = tmp["b_array_0"]
        NN_coeffs['b_array_1'] = tmp["b_array_1"]
        NN_coeffs['b_array_2'] = tmp["b_array_2"]
        NN_coeffs['x_min'] = tmp["x_min"]
        NN_coeffs['x_max'] = tmp["x_max"]
        tmp.close()

    return NN_coeffs


def spectrum(x,*pars) :
    """ Return full spectrum given input list of pixels, parameters
    """
    scaled_labels = (np.array(pars)-NN_coeffs['x_min'])/(NN_coeffs['x_max']-NN_coeffs['x_min']) - 0.5
    #pdb.set_trace()
    #inside = np.einsum('ij,j->i', NN_coeffs['w_array_0'], scaled_labels) + NN_coeffs['b_array_0']
    #outside = np.einsum('ij,j->i', NN_coeffs['w_array_1'], sigmoid(inside)) + NN_coeffs['b_array_1']
    #spec = np.einsum('ij,j->i', NN_coeffs['w_array_2'], sigmoid(outside)) + NN_coeffs['b_array_2']

    tmp = np.dot(NN_coeffs['w_array_0'],scaled_labels)+NN_coeffs['b_array_0']
    nlayers=len(NN_coeffs['num_neurons'])
    for i in range(nlayers) :
        spec = np.dot(sigmoid(tmp),NN_coeffs['w_array_{:d}'.format(i+1)].T)+NN_coeffs['b_array_{:d}'.format(i+1)]
        tmp = spec

    return spec

def test(pmn, pstd, mn, std, weights, biases,n=100, t0=[3750.,4500.], g0=2., mh0=0.) :
    """ Plots cross-sections of model for fit pixels
    """
    fig,ax=plots.multi(2,6,figsize=(8,12))

    xt=['Teff','logg','[M/H]','[alpha/M]','[C/M]','[N/M]']
    for i,ipar in enumerate([0,1,2,3,4,5]) : 
      for ipix in range(len(weights)) :
       for it0 in range(2) :
        pars=np.tile([t0[it0], g0, mh0, 0.0, 0., 0., 2.],(n,1))
        if ipar == 0 : pars[:,ipar]=np.linspace(3000.,8000.,n)
        elif ipar == 1 : pars[:,ipar]=np.linspace(-0.5,5.5,n)
        elif ipar == 2 : pars[:,ipar]=np.linspace(-2.5,1.,n)
        elif ipar == 3 : pars[:,ipar]=np.linspace(-0.5,1.0,n)
        elif ipar == 4 : pars[:,ipar]=np.linspace(-1.,1.,n)
        elif ipar == 5 : pars[:,ipar]=np.linspace(-0.5,2.,n)
        m=[]
        for ip in range(pars.shape[0]) : m.append(model((pars[ip,:]-pmn)/pstd,mn[ipix],std[ipix],weights[ipix],biases[ipix]))
        plots.plotl(ax[i,it0],pars[:,ipar],m,xt=xt[i])
        #m=[]
        #for ip in range(pars.shape[0]) : m.append(nets[ipix].predict((pars[ip,:].reshape(1,7)-pmn)/pstd)[0,0]*std[ipix]+mn[ipix])
        #plots.plotl(ax[i,it0],pars[:,ipar],m)
        if i == 0 : ax[i,it0].set_title('{:8.0f}{:7.2f}{:7.2f}'.format(t0[it0],g0,mh0))
    fig.tight_layout()

def fitinput(file,model,threads=8,nfit=8,dofit=True,order=4,pixel_model=False,norm=False,raw=False, mcmc=False,err=0.005) :
    """ Solves for parameters using input spectra and NN model
    """
    if pixel_model: mod=get_model_pixel(model)
    else : mod=get_model(model)

    s, p = read(file,raw=raw, label_names=mod['label_names'])
    if nfit == 0 : nfit = p.shape[0]

    nlab=len(mod['label_names'])
    init=np.zeros(nlab)
    bounds_lo=mod['x_min']
    bounds_hi=mod['x_max']

    j=np.where(np.core.defchararray.strip(mod['label_names']) == 'Teff')[0]
    init[j] = 4000.
    j=np.where(np.core.defchararray.strip(mod['label_names']) == 'logg')[0]
    init[j] = 2.5
    j=np.where(np.core.defchararray.strip(mod['label_names']) == 'vmicro')[0]
    init[j] = 1.2

    #if rot:
    #    init = np.array([4000.,2.5,0.,0.,0.,0.,1.5,0.])
    #    bounds = (np.array([3000.,-0.5,-3.,-1.,-1.5,-1.,0.3,0.]),
    #              np.array([8000., 5.5, 1., 1., 1., 2.,4.5,100.]))
    #else :
    #    init = np.array([4000.,2.5,0.,0.,0.,0.,1.5])
    #    bounds = (np.array([3000.,-0.5,-3.,-1.,-1.5,-1.,0.3]),
    #              np.array([8000., 5.5, 1., 1., 1., 2.,4.5]))

    specerr=np.full_like(s[0,:],err)
    if dofit :
        npix=s.shape[1]
        specs=[]
        for i in range(nfit) :
            obs = s[i,:]+specerr*np.random.randn(npix)
            if norm : 
                cont = norm.cont(obs,specerr,poly=True,order=order,chips=True)
                specs.append((obs/cont, specerr, init, (bounds_lo,bounds_hi)))
            else:
                specs.append((obs, specerr, init, (bounds_lo,bounds_hi)))

        pdb.set_trace()
        if threads==0 :
            output=[]
            for i in range(nfit) :
                out=solve(specs[i])
            output.append(out)
        else :
            pool = mp.Pool(threads)
            output = pool.map_async(solve, specs).get()
            pool.close()
            pool.join()
        output=np.array(output)

        if mcmc :
            newspecs=[]
            for i in range(nfit) :
                newspecs.append((specs[i][0],specs[i][1],output[i,:]))
            pdb.set_trace()
            for i in range(0,nfit,10) :
                out=solve_mcmc(newspecs[i])


        # plot output minus input parameters 
        pdb.set_trace()
        fig,ax=plots.multi(2,nlab,hspace=0.001,wspace=0.0012)
        for i,label in enumerate(mod['label_names']) :
            if label == 'Teff' : yr=[-250,250]
            else : yr=[-0.5,0.5]
            plots.plotc(ax[i,0],p[0:nfit,0],output[:,i]-p[0:nfit,i],p[0:nfit,2],yr=yr,yt=label)
            plots.plotc(ax[i,1],p[0:nfit,i],output[:,i]-p[0:nfit,i],p[0:nfit,0],yr=yr,yt=label)
        #plots.plotc(ax[0,0],p[0:nfit,0],output[:,0]-p[0:nfit,0],p[0:nfit,2],yr=[-250,250],yt='Teff')
        #plots.plotc(ax[1,0],p[0:nfit,0],output[:,1]-p[0:nfit,1],p[0:nfit,2],yr=[-1,1],yt='logg')
        #plots.plotc(ax[2,0],p[0:nfit,0],output[:,2]-p[0:nfit,2],p[0:nfit,2],yr=[-0.5,0.5],yt='[M/H]')
        #plots.plotc(ax[3,0],p[0:nfit,0],output[:,3]-p[0:nfit,3],p[0:nfit,2],yr=[-0.5,0.5],yt='[alpha/M]')
        #plots.plotc(ax[0,1],p[0:nfit,0],output[:,4]-p[0:nfit,4],p[0:nfit,2],yr=[-0.5,0.5],yt='[C/M]')
        #plots.plotc(ax[1,1],p[0:nfit,0],output[:,5]-p[0:nfit,5],p[0:nfit,2],yr=[-0.5,0.5],yt='[N/M]')
        #plots.plotc(ax[2,1],p[0:nfit,0],output[:,6]-p[0:nfit,6],p[0:nfit,2],yr=[-0.5,0.5],yt='vmicro')
        fig.savefig(file+'_out.png')
        # write the spectra out
        hdu=fits.HDUList()
        hdu.append(fits.ImageHDU(output))
        hdu.writeto(file+'_out.fits',overwrite=True)
        hdu.close()

    # save model and fit spectra
    pdb.set_trace()
    pix = np.arange(0,8575,1)
    model=[]
    fig,ax=plots.multi(1,1)
    ax2=ax.twinx()
    ax2.set_ylim(-0.1,0.1)
    for i in range(nfit) :
        snorm = s[i,:] / np.nanmean(s[i,:])
        gd = np.where(np.isfinite(s[i,:]))[0]
        pars=p[i,0:nlab]
        spec=spectrum(pix, *pars)
        fit=spectrum(pix, *output[i,:])    
        ax.cla()
        ax2.cla()
        plots.plotl(ax,pix[gd],s[i,:])
        plots.plotl(ax,pix[gd],fit)
        plots.plotl(ax2,pix[gd],(s[i,gd]-fit))
        plots.plotl(ax,pix[gd],spec)
        plots.plotl(ax2,pix[gd],(s[i,gd]-spec))
        model.append(spec)
        print(pars)
        print(output[i,:])
        print(output[i,:]-pars)
        pdb.set_trace()

    hdu=fits.HDUList()
    hdu.append(fits.ImageHDU(np.array(model)))
    hdu.writeto(file+'_model.fits',overwrite=True)   
    hdu.close()


def dclip(d,lim=[-0.5,0.5]) :
    d[np.where(d < lim[0])[0]]=lim[0]
    d[np.where(d > lim[1])[0]]=lim[1]
    return d

def comp(file,order=4,z=2)  :
    """ Plot results of testinput vs true parameters
    """
    p=fits.open(file+'.fits')[0].data
    s=fits.open(file+'.fits')[2].data
    out=fits.open(file+'_out.fits')[0].data
    fit=fits.open(file+'_model.fits')[0].data
    specerr=np.full_like(s[0,:],0.005)

    fig,ax=plots.multi(2,7,hspace=0.001,wspace=0.5)
    plots.plotc(ax[0,0],p[:,0],out[:,0]-p[:,0],p[:,z],xt='Teff',yt=r'$\Delta$Teff') #,yr=[-200,200])
    plots.plotc(ax[1,0],p[:,0],out[:,1]-p[:,1],p[:,z],xt='Teff',yt=r'$\Delta$logg') #,yr=[-0.5,0.5])
    plots.plotc(ax[2,0],p[:,0],out[:,2]-p[:,2],p[:,z],xt='Teff',yt=r'$\Delta$[M/H]') #,yr=[-0.5,0.5])
    plots.plotc(ax[3,0],p[:,0],out[:,3]-p[:,3],p[:,z],xt='Teff',yt=r'$\Delta$[a/M]') #,yr=[-0.5,0.5])
    plots.plotc(ax[4,0],p[:,0],out[:,4]-p[:,4],p[:,z],xt='Teff',yt=r'$\Delta$[C/M]') #,yr=[-0.5,0.5])
    plots.plotc(ax[5,0],p[:,0],out[:,5]-p[:,5],p[:,z],xt='Teff',yt=r'$\Delta$[N/M]') #,yr=[-0.5,0.5])
    plots.plotc(ax[6,0],p[:,0],out[:,6]-p[:,6],p[:,z],xt='Teff',yt=r'$\Delta$vmicro') #,yr=[-0.5,0.5])
    ax[0,1].hist(dclip(out[:,0]-p[:,0],lim=[-200,200]),bins=np.arange(-200,201,10),histtype='step')
    ax[1,1].hist(dclip(out[:,1]-p[:,1]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    ax[2,1].hist(dclip(out[:,2]-p[:,2]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    ax[3,1].hist(dclip(out[:,3]-p[:,3]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    ax[4,1].hist(dclip(out[:,4]-p[:,4]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    ax[5,1].hist(dclip(out[:,5]-p[:,5]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    ax[6,1].hist(dclip(out[:,6]-p[:,6]),bins=np.arange(-0.5,0.51,0.01),histtype='step')
    fig.suptitle(file)
    pdb.set_trace()

    for i in range(s.shape[0]) :
        cont = norm.cont(s[i,:],specerr,poly=True,order=order,chips=True)
        print('{:8.1f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}'.format(
               p[i,0],p[i,1],p[i,2],p[i,3],p[i,4],p[i,5],p[i,6],p[i,7]))
        print('{:8.1f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}{:7.2f}'.format(
               out[i,0],out[i,1],out[i,2],out[i,3],out[i,4],out[i,5],out[i,6],out[i,7]))

        plt.clf()
        plt.plot(s[i,:]/cont,color='b')
        plt.plot(fit[i,:],color='r')
        plt.plot(fit[i,:]/(s[i,:]/cont)+0.1,color='g')
        #if dofit :
        #    print(output[i])
        #    fit=spectrum(pix, *output[i])
        #    gd=np.where(np.isfinite(snorm))[0]
        #    print(np.sum((spec[gd]-snorm[gd])**2),np.sum((fit[gd]-snorm[gd])**2))
        #    plt.plot(fit,color='b')
        plt.draw()
        pdb.set_trace()

def lnprior(pars) :
    return 0.

def lnprob(pars,s,serr) :
    model=spectrum(s,*pars)
    return -0.5*np.sum((s-model)**2/serr**2) + lnprior(pars)
    
def solve_mcmc(spec, nburn=50, nsteps=500, nwalkers=100, eps=0.01) :
    s=spec[0]
    serr=spec[1]
    init=spec[2]
    ndim = len(init)
    pix = np.arange(0,len(s),1)
    gd = np.where(np.isfinite(s))[0]
    pos = [init + eps*np.random.randn(ndim)*init for i in range(nwalkers)]
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, args=(s[gd], serr[gd]))
    print(init)
    print('running mcmc...')
    sampler.run_mcmc(pos, nsteps)
    samples = sampler.chain[:, nburn:, :].reshape((-1, ndim))
    corner.corner(samples,show_titles=True,quantiles=[0.05,0.95])
    pdb.set_trace()


def solve(spec) :
    """ Solve for parameters for a single input spectrum
    """
    s=spec[0]
    serr=spec[1]
    init=spec[2]
    bounds=spec[3]
    pix = np.arange(0,len(s),1)
    gd = np.where(np.isfinite(s))[0]
    try:
        fpars,fcov = curve_fit(spectrum,pix[gd],s[gd],sigma=serr[gd],p0=init,bounds=bounds)
    except ValueError:
        print("Error - value error")
        print(init)
        fpars=init*0.
    except RuntimeError:
        print("Error - curve_fit failed")
        fpars=init*0.

    return fpars

def fitfield(model,field,stars=None,nfit=0,order=4,threads=8,plot=False,write=True) :
    """ Fit observed spectra in an input field, given a model
    """

    # get model and list of stars
    get_model_pixel(model)
    load=apload.ApLoad(dr='dr14')
    apfield=load.apField(field)[1].data
    aspcap_param=load.aspcapField(field)[1].data
    aspcap_spec=load.aspcapField(field)[2].data
    if stars is None :
        stars=apfield['apogee_id']
        if nfit == 0 : stars = stars[0:nfit]
 
    # load up normalized spectra and uncertainties 
    specs=[]
    if plot : fig,ax=plots.multi(1,2,hspace=0.001,figsize=(15,3))
    pix = np.arange(0,8575,1)
    for star in stars :
        apstar=dr14load.apStar(field,star)
        spec = apstar[1].data[0,:].squeeze()
        specerr = apstar[2].data[0,:].squeeze()
        cont = norm.cont(spec,specerr,poly=True,order=order,chips=True)
        specs.append((spec/cont,specerr/cont))
        if plot :
            ax[0].cla()
            ax[1].cla()
            ax[0].plot(spec)
            ax[0].plot(cont)
            ax[1].plot(spec/cont)
            j=np.where(aspcap_param['APOGEE_ID'] == star)[0][0]
            aspec=aspcap.aspcap2apStar(aspcap_spec[j]['spec'])
            ax[1].plot(aspec,color='r')
            plt.draw()
            plt.show()
            pdb.set_trace()

    # do the fits in parallel
    pool = mp.Pool(threads)
    output = pool.map_async(solve, specs).get()
    pool.close()
    pool.join()
    print('done pool')

    # output FITS table
    output=np.array(output)
    out=Table()
    out['APOGEE_ID']=stars
    length=len(out)
    out.add_column(Column(name='FPARAM',data=output))
    spec=[]
    err=[]
    bestfit=[]
    chi2=[]
    for i,star in enumerate(stars) :
        spec.append(specs[i][0])
        err.append(specs[i][1])
        fit=spectrum(pix, *output[i])
        bestfit.append(fit)
        chi2.append(np.nansum((specs[i][0]-fit)**2/specs[i][1]**2))
    out.add_column(Column(name='SPEC',data=np.array(spec)))
    out.add_column(Column(name='ERR',data=np.array(err)))
    out.add_column(Column(name='SPEC_BESTFIT',data=np.array(bestfit)))
    out.add_column(Column(name='CHI2',data=np.array(chi2)))
    if write : out.write('nn-'+field+'.fits',format='fits',overwrite=True)
    return out

def aspcap_comp(model,fields,plot=True,save=None,loggmax=99) :
    """ Compare NN results with ASPCAP 
    """

    get_model_pixel(model)
    load=apload.ApLoad(dr='dr14')

    apars_all=[]
    npars_all=[]
    if plot :    fig,ax=plots.multi(1,3,hspace=0.001,figsize=(15,3),sharex=True)
    for field in fields :
      try :
        out=fits.open('nn-'+field+'.fits')[1].data
        nfit = len(out)
        print(field,nfit)
        apfield=load.apField(field)[1].data
        aspcap_param=load.aspcapField(field)[1].data
        aspcap_spec=load.aspcapField(field)[2].data
        stars=apfield['apogee_id']

        # look at results for each spectrum
        pix = np.arange(0,8575,1)

        for i in range(nfit) :
            print(i,stars[i])
            j=np.where((aspcap_param['APOGEE_ID'] == stars[i]) & (aspcap_param['FPARAM'][:,1] < loggmax))[0]
            if len(j) > 0 :
              j=j[0]
              fp=aspcap_param[j]['FPARAM'].squeeze()
              apars=np.array([fp[0],fp[1],fp[3],fp[6],fp[4],fp[5],10.**fp[2]])
              apars_all.append(apars)
              npars_all.append(out['FPARAM'][i,:])
              if plot and np.abs(out['FPARAM'][i,0]-fp[0]) > 1000:
                pprint(out[i]['FPARAM'])
                ax[0].cla()
                ax[0].plot(out[i]['SPEC'],color='k')
                ax[0].plot(out[i]['ERR'],color='k',ls='dotted')
                ax[0].set_ylim(0.5,1.5)
                ax[1].cla()
                ax[1].plot(out[i]['SPEC'],color='k')
                ax[1].plot(out[i]['SPEC_BESTFIT'],color='b')
                ax[1].set_ylim(0.5,1.5)
                print('nn chi2: ',np.nansum((out[i]['SPEC']-out[i]['SPEC_BESTFIT'])**2/out[i]['ERR']**2))
                ax[2].plot((out[i]['SPEC']-out[i]['SPEC_BESTFIT'])**2/out[i]['ERR']**2,color='b')
                # using ASPCAP parameters and NN model
                # plot ASPCAP normalized spectrum
                aspec=aspcap.aspcap2apStar(aspcap_spec[j]['spec'])
                aerr=aspcap.aspcap2apStar(aspcap_spec[j]['err'])
                print('nn chi2 with aerr: ',np.nansum((out[i]['SPEC']-out[i]['SPEC_BESTFIT'])**2/aerr**2))
                ax[0].plot(aspec,color='r')
                ax[0].plot(aerr,color='r',ls='dotted')
                pprint(apars)
                print('rot: ',fp[7])
                print(aspcap_param[j]['FPARAM_CLASS'][0:3],aspcap_param[j]['CHI2_CLASS'][0:3])
                # NN model with ASPCAP params
                fit=spectrum(pix, *apars)
                print('nn(ASPCAP) chi2',np.nansum((out[i]['SPEC']-fit)**2/out[i]['ERR']**2))
                print('nn(ASPCAP) chi2 with aerr',np.nansum((out[i]['SPEC']-fit)**2/aerr**2))
                ax[1].plot(fit,color='g')
                ax[2].plot((out[i]['SPEC']-fit)**2/out[i]['ERR']**2,color='g')
                # ASPCAP model
                aspec=aspcap.aspcap2apStar(aspcap_spec[j]['spec_bestfit'])
                ax[1].plot(aspec,color='r')
                plt.draw()
                plt.show()
                pdb.set_trace()
      except : pass

    apars_all=np.array(apars_all)
    npars_all=np.array(npars_all)
    fig,ax=plots.multi(2,1,hspace=0.001,wspace=0.001)
    plots.plotc(ax[0],npars_all[:,0],npars_all[:,1],npars_all[:,2],xr=[8000,3000],yr=[5,0],zr=[-2,0.5])
    plots.plotc(ax[1],apars_all[:,0],apars_all[:,1],apars_all[:,2],xr=[8000,3000],yr=[5,0],zr=[-2,0.5])
    if save is not None :
        fig.savefig(save+'_hr.png')

    fig,ax=plots.multi(2,7,hspace=0.001,wspace=0.001)
    yt=['Teff','logg','[M/H]','[alpha/M]','[C/M]','[N/M]','vmicro']
    for i in range(7) :
      plots.plotc(ax[i,0],apars_all[:,0],npars_all[:,i]-apars_all[:,i],apars_all[:,2],xr=[8100,2900],zr=[-2,0.5],size=20,yt=yt[i])
      plots.plotc(ax[i,1],apars_all[:,i],npars_all[:,i]-apars_all[:,i],apars_all[:,0],zr=[2900,8100],size=20)
    if save is not None :
        fig.savefig(save+'.png')

def pprint(pars) :
    print('{:8.1f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}'.format(*pars))


def showtime(string) :
    """ Utiltiy routine to print a string and clock time
    """
    print(string+' {:8.2f}'.format(time.time()))
    sys.stdout.flush()


def train(file='all_noelem',name='test',plot=False,suffix='',fitfrac=0.5, steps=1e5, weight_decay = 0., num_neurons = [300,300], lr=0.001,
          teff=[0,10000],logg=[-1,6],mh=[-3,1],am=[-1,1],cm=[-2,2],nm=[-2,2],raw=True,rot=False,elem=False,norm=False,elems=None,label_names=None) :
    """ Train a neural net model on an input training set
    """

    spectra, labels = read(file,raw=raw, label_names=label_names)

    # shuffle them and get fit and validation set
    print('shuffling...')
    shape=labels.shape
    ind_shuffle=np.random.permutation(shape[0])

    #----------------------------------------------------------------------------------------
    # choose only a certain labels
    ind_label= np.arange(9)

    gd=np.where((labels[ind_shuffle,0]>=teff[0]) & (labels[ind_shuffle,0]<=teff[1]) &
                (labels[ind_shuffle,1]>=logg[0]) & (labels[ind_shuffle,1]<=logg[1]) &
                (labels[ind_shuffle,2]>=mh[0]) & (labels[ind_shuffle,2]<=mh[1]) &
                (labels[ind_shuffle,3]>=am[0]) & (labels[ind_shuffle,3]<=am[1]) &
                (labels[ind_shuffle,4]>=cm[0]) & (labels[ind_shuffle,4]<=cm[1])  &
                (labels[ind_shuffle,5]>=nm[0]) & (labels[ind_shuffle,5]<=nm[1])
               )[0]
 

    nfit = int(fitfrac*len(gd))
    # separate into training and validation set
    training_spectra = spectra[ind_shuffle[gd],:][:nfit,:]
    training_labels = labels[ind_shuffle[gd],:][:nfit,:][:,ind_label]
    validation_spectra = spectra[ind_shuffle[gd],:][nfit:,:]
    validation_labels = labels[ind_shuffle[gd],:][nfit:,:][:,ind_label]

    model = training.neural_net(training_labels, training_spectra,\
                                validation_labels, validation_spectra,\
                                num_neurons = num_neurons, num_steps=steps, learning_rate=lr, weight_decay=weight_decay)
    model['label_names' ] = label_names
    model['data_file' ] = file
    model['nfit' ] = nfit
    model['ind_shuffle' ] = ind_shuffle[gd]
    model['teff_lim' ] = teff
    model['logg_lim' ] = logg
    model['mh_lim' ] = mh
    model['am_lim' ] = am
    model['cm_lim' ] = cm
    model['nm_lim' ] = nm
    model['learning_rate' ] = lr
    model['weight_decay' ] = weight_decay
    model['num_neurons' ] = num_neurons
    model['steps' ] = steps

    with open('{:s}.pkl'.format(name), 'wb') as f:  
        pickle.dump(model, f, protocol=2)

def read(file,raw=True,label_names=None) :
    """ Read input spectra and parameters
    """
    hdulist = fits.open(file+'.fits')
    if raw : spectra = hdulist[1].data.astype("float")
    else : spectra = hdulist[2].data.astype("float")
    print(spectra.shape)
    gdpix=np.where(np.isfinite(spectra[0,:]))[0]
    spectra=spectra[:,gdpix]
    print(spectra.shape)

    # read labels
    labels = hdulist[0].data
    labels = np.array([labels[i] for i in range(len(labels))])

    try :
        all_label_names=[]
        for i in range(hdulist[0].header['NPAR']) :
            all_label_names.append(hdulist[0].header['PAR{d}'.format(i)])
        all_label_names=np.array(all_label_names)
    except :
        all_label_names=ascii.read(file).colnames

    if label_names is not None :
        ind_label = []
        for label in label_names :
            j = np.where(np.core.defchararray.strip(all_label_names) == label)[0]
            ind_label.extend(j)
        ind_label = np.array(ind_label)
    else :
        ind_label = np.arange(len(all_label_names))

    return spectra, labels[:,ind_label]

def plot(file='all_noelem',model='GKh_300_0',raw=True,plotspec=False,validation=True,
         teff=[0,10000],logg=[-1,6],mh=[-3,1],am=[-1,1],cm=[-2,2],nm=[-2,2]) :
    ''' plots to assess quality of a model
    '''
    # load model and set up for use
    NN_coeffs = get_model(model)

    # read spectra and labels, and get indices for training and validation set
    true,labels = read(file,raw=raw,label_names=NN_coeffs['label_names'])

    if validation : 
        nfit = NN_coeffs['nfit']
        ind_shuffle = NN_coeffs['ind_shuffle']
        true = true[ind_shuffle]
        gd=np.where((labels[:,0]>=teff[0]) & (labels[:,0]<=teff[1]) &
                    (labels[:,1]>=logg[0]) & (labels[:,1]<=logg[1]) &
                    (labels[:,2]>=mh[0]) & (labels[:,2]<=mh[1]) &
                    (labels[:,3]>=am[0]) & (labels[:,3]<=am[1]) &
                    (labels[:,4]>=cm[0]) & (labels[:,4]<=cm[1])  &
                    (labels[:,5]>=nm[0]) & (labels[:,5]<=nm[1]) 
                   )[0]
        true = true[gd]
        labels = labels[gd]
    else :
        nfit = 0
        ind_shuffle = np.arange(true.shape[0])

    # loop over the spectra
    if plotspec: plt.figure()
    nn=[]
    for i,lab in enumerate(labels[ind_shuffle]) :
        # calculate model spectrum and accumulate model array
        pix = np.arange(8575)
        spec = spectrum(pix, *lab)
        nn.append(spec)
        #if plotspec :
        #    plt.clf()
        #    plt.plot(true[i,j])
        #    plt.plot(apstar[j])
        #    plt.plot(apstar[j]/true[i,j])
        #    plt.show()
        #    pdb.set_trace()
        #n=len(np.where(np.abs(apstar[j]-true[i,j]) > 0.05)[0])
    nn=np.array(nn)

    # histogram of ratio of nn to true
    print("making nn/raw comparison histogram ...")
    # pixels across sample
    fig,ax=plots.multi(2,2)
    # percentiles across wavelength
    fig2,ax2=plots.multi(1,3,hspace=0.001)
    # in parameter space
    fig3,ax3=plots.multi(2,3,hspace=0.001,wspace=0.001)

    # consider full sample and several bins in Teff and [M/H]
    tbins=[[3000,8000],[3500,4000],[4000,5000],[5000,6000],[3500,4000],[4000,5000],[5000,6000]]
    mhbins=[[-2.5,1.0],[-0.5,1.0],[-0.5,1.0],[-0.5,1.0],[-2.5,-0.5],[-2.5,-0.5],[-2.5,-0.5]]
    names=['all','3500<Te<4000, M/H>-0.5','4000<Te<5000, M/H>-0.5','5000<Te<6000, M/H>-0.5',
                 '3500<Te<4000, M/H<-0.5','4000<Te<5000, M/H<-0.5','5000<Te<6000, M/H<-0.5']
    colors=['k','r','g','b','c','m','y']
    lws=[3,1,1,1,1,1,1]

    for tbin,mhbin,name,color,lw in zip(tbins,mhbins,names,colors,lws) :
        # validation set
        gd = np.where( (labels[ind_shuffle[nfit:],0] > tbin[0]) & (labels[ind_shuffle[nfit:],0] < tbin[1]) &
                       (labels[ind_shuffle[nfit:],2] > mhbin[0]) & (labels[ind_shuffle[nfit:],2] < mhbin[1])) [0]
        if len(gd) > 0 :
            t1=nn[nfit+gd,:]
            t2=true[nfit+gd,:]

            # differential fractional error of all pixels
            err=(t1-t2)/t2
            hist,bins=np.histogram(err.flatten(),bins=np.linspace(-0.2,0.2,4001))
            plots.plotl(ax[0,0],np.linspace(-0.200+0.005,0.2,4000),hist/hist.sum(),semilogy=True,xt='nn/true',
                        label=name,xr=[-0.2,0.5],color=color,linewidth=lw)
            ax[0,0].legend(fontsize='x-small')

            # cumulative fractional error of all pixels
            err=np.abs(err)
            hist,bins=np.histogram(err.flatten(),bins=np.logspace(-7,3,501))
            plots.plotl(ax[0,1],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),xt='nn/true',
                        label=name,color=color,linewidth=lw)
            ax[0,1].set_ylabel('Cumulative fraction, all pixels')

            # get percentiles across models at each wavelength
            p=[50,95,99]
            perc=np.percentile(err,p,axis=0)
            npix=perc.shape[1]
            for i in range(3) : 
                plots.plotl(ax2[i],np.arange(npix),perc[i,:],color=color,linewidth=lw,xt='Pixel number')
                ax2[i].text(0.05,0.9,'error at {:d} percentile'.format(p[i]),transform=ax2[i].transAxes)

            # cumulative of 50 and 95 percentile across models
            hist,bins=np.histogram(perc[0,:],bins=np.logspace(-7,3,501))
            plots.plotl(ax[1,0],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),color=color,ls=':',linewidth=lw)
            hist,bins=np.histogram(perc[1,:],bins=np.logspace(-7,3,501))
            plots.plotl(ax[1,0],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),color=color,linewidth=lw)
            ax[1,0].set_ylabel('Cumulative, perc across models')

            # cumulative of 50 and 95 percentile across wavelengths
            p=[50,95,99]
            perc=np.percentile(err,p,axis=1)
            hist,bins=np.histogram(perc[0,:],bins=np.logspace(-7,3,501))
            plots.plotl(ax[1,1],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),color=color,ls=':',linewidth=lw)
            hist,bins=np.histogram(perc[1,:],bins=np.logspace(-7,3,501))
            plots.plotl(ax[1,1],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),color=color,linewidth=lw)
            ax[1,1].set_ylabel('Cumulative, perc across wave')

            for ix,iy in zip([1,0,1],[0,1,1]) :
                ax[iy,ix].set_xlim(0.,0.01)
                ax[iy,ix].set_ylim(0.,1.0)
                ax[iy,ix].set_xlabel('|nn-true|')
                ax[iy,ix].set_xscale('log')
                ax[iy,ix].set_xlim(1.e-4,0.01)

            # Kiel diagram plots color-coded
            if lw == 3 :
                # color-code by value of 50, 95, and 99 percentile of wavelengths for each model
                p=[50,95,99]
                perc_mod=np.percentile(err,p,axis=1)
                dx=np.random.uniform(size=len(gd))*50-25
                dy=np.random.uniform(size=len(gd))*0.2-0.1
                for i in range(3) :
                    plots.plotc(ax3[i,0],labels[ind_shuffle[nfit+gd],0]+dx,labels[ind_shuffle[nfit+gd],1]+dy,perc_mod[i,:],
                                xr=[8000,3000],yr=[6,-1],zr=[0,0.1],xt='Teff',yt='log g')
                    ax3[i,0].text(0.1,0.9,'error at {:d} percentile'.format(p[i]),transform=ax3[i,0].transAxes)
                # color-code by fraction of pixels worse than 0.01
                for i,thresh in enumerate([0.01,0.05,0.1]):
                    mask=copy.copy(err)
                    mask[mask<=thresh] = 0
                    mask[mask>thresh] = 1
                    bdfrac=mask.sum(axis=1)/mask.shape[1]
                    axim=plots.plotc(ax3[i,1],labels[ind_shuffle[nfit+gd],0]+dx,labels[ind_shuffle[nfit+gd],1]+dy,bdfrac,
                                xr=[8000,3000],yr=[6,-1],zr=[0,0.1],xt='Teff')
                    ax3[i,1].text(0.1,0.9,'Fraction of pixels> {:4.2f}'.format(thresh),transform=ax3[i,1].transAxes)
                cax = plt.axes([0.05, 0.03, 0.9, 0.02])
                fig3.colorbar(axim,cax=cax,orientation='horizontal')


        # training set
        #gd = np.where( (labels[ind_shuffle[:nfit],0] > tbin[0]) & (labels[ind_shuffle[:nfit],0] < tbin[1]) &
        #               (labels[ind_shuffle[:nfit],2] > mhbin[0]) & (labels[ind_shuffle[:nfit],2] < mhbin[1])) [0]
        #if len(gd) > 0 :
        #    t1=nn[gd,:]
        #    t2=true[gd,:]
        #    hist,bins=np.histogram((t1/t2).flatten(),bins=np.linspace(0.8,1.2,4001))
        #    plots.plotl(ax[1,0],np.linspace(0.8005,1.2,4000),hist/hist.sum(),semilogy=True,xt='nn/true',label=name,xr=[0.8,1.5],color=color,linewidth=lw)
        #    hist,bins=np.histogram(np.abs(((t1-t2)/t2).flatten()),bins=np.logspace(-7,3,501))
        #    plots.plotl(ax[1,1],np.logspace(-7,3,500),np.cumsum(hist)/np.float(hist.sum()),xt='nn/true',label=name,color=color,linewidth=lw)
        #    ax[1,1].set_xlim(0.,0.01)
        #    ax[1,1].set_ylim(0.,1.0)
        #    ax[1,1].set_xlabel('|nn-true|')
        #    ax[1,1].set_ylabel('Cumulative fraction')

    fig.tight_layout()
    plt.draw()
    fig.savefig(file+'_'+model+'_1.png')
    fig2.savefig(file+'_'+model+'_2.png')
    fig3.savefig(file+'_'+model+'_3.png')
    pdb.set_trace()
    plt.close()
    plt.close()
    plt.close()
    return nn, true

if __name__ == '__main__' :

    #train( name='alllo', raw=False)
    #train( name='allhi', raw=True)
    train( teff=[3000,4000], mh=[-0.5,0.75] , name='Mhlo', raw=False)
    train( teff=[3000,4000], mh=[-0.5,0.75] , name='Mhhi', raw=True)
    #train( teff=[3500,6000], mh=[-0.5,0.75] , name='GKhlo', raw=False)
    #train( teff=[3500,6000], mh=[-0.5,0.75] , name='GKhhi', raw=True)
    #train( teff=[5500,8000], mh=[-0.5,0.75] , name='Fhlo', raw=False)
    #train( teff=[5500,8000], mh=[-0.5,0.75] , name='Fhhi', raw=True)
