import copy

import matplotlib as mpl
import matplotlib.pyplot as plt
from astropy import wcs
import astropy.io.fits as pyfits
import pywcsgrid2
import numpy as np
from numpy import ma
import matplotlib.cbook as cbook
from matplotlib.colors import NoNorm, LogNorm, Normalize

from fermipy.utils import merge_dict, AnalysisBase


def load_ds9_cmap():
    # http://tdc-www.harvard.edu/software/saoimage/saoimage.color.html
    ds9_b = {
        'red'   : [[0.0 , 0.0 , 0.0], 
                   [0.25, 0.0 , 0.0], 
                   [0.50, 1.0 , 1.0], 
                   [0.75, 1.0 , 1.0], 
                   [1.0 , 1.0 , 1.0]],
        'green' : [[0.0 , 0.0 , 0.0], 
                   [0.25, 0.0 , 0.0], 
                   [0.50, 0.0 , 0.0], 
                   [0.75, 1.0 , 1.0], 
                   [1.0 , 1.0 , 1.0]],
        'blue'  : [[0.0 , 0.0 , 0.0], 
                   [0.25, 1.0 , 1.0], 
                   [0.50, 0.0 , 0.0], 
                   [0.75, 0.0 , 0.0], 
                   [1.0 , 1.0 , 1.0]]
        }
     
    plt.register_cmap(name='ds9_b', data=ds9_b) 
    plt.cm.ds9_b = plt.cm.get_cmap('ds9_b')
    return plt.cm.ds9_b

class PowerNorm(mpl.colors.Normalize):
    """
    Normalize a given value to the ``[0, 1]`` interval with a power-law
    scaling. This will clip any negative data points to 0.
    """
    def __init__(self, gamma, vmin=None, vmax=None, clip=True):
        mpl.colors.Normalize.__init__(self, vmin, vmax, clip)
        self.gamma = gamma

    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        self.autoscale_None(result)
        gamma = self.gamma
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin == vmax:
            result.fill(0)
        else:
            if clip:
                mask = ma.getmask(result)
                val = ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                mask=mask)
            resdat = result.data
            resdat -= vmin
            np.power(resdat, gamma, resdat)
            resdat /= (vmax - vmin) ** gamma
            result = np.ma.array(resdat, mask=result.mask, copy=False)
            result[(value < 0)&~result.mask] = 0
        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        gamma = self.gamma
        vmin, vmax = self.vmin, self.vmax

        if cbook.iterable(value):
            val = ma.asarray(value)
            return ma.power(value, 1. / gamma) * (vmax - vmin) + vmin
        else:
            return pow(value, 1. / gamma) * (vmax - vmin) + vmin

    def autoscale(self, A):
        """
        Set *vmin*, *vmax* to min, max of *A*.
        """
        self.vmin = ma.min(A)
        if self.vmin < 0:
            self.vmin = 0
            warnings.warn("Power-law scaling on negative values is "
                          "ill-defined, clamping to 0.")

        self.vmax = ma.max(A)

    def autoscale_None(self, A):
        """ autoscale only None-valued vmin or vmax"""
        if self.vmin is None and np.size(A) > 0:
            self.vmin = ma.min(A)
            if self.vmin < 0:
                self.vmin = 0
                warnings.warn("Power-law scaling on negative values is "
                              "ill-defined, clamping to 0.")

        if self.vmax is None and np.size(A) > 0:
            self.vmax = ma.max(A)

class ImagePlotter(object):

    def __init__(self,fitsfile):

        hdulist = pyfits.open(fitsfile)        
        header = hdulist[0].header
        header = pyfits.Header.fromstring(header.tostring())
        self._wcs = wcs.WCS(header)

        self._data = copy.deepcopy(hdulist[0].data)
        
    def plot(self,subplot=111,catalog=None,cmap='jet',**kwargs):

        

        kwargs_contour = { 'levels' : None, 'colors' : ['k'],
                           'linewidths' : None,
                           'origin' : 'lower' }
        
        kwargs_imshow = { 'interpolation' : 'nearest',
                          'origin' : 'lower','norm' : None,
                          'vmin' : None, 'vmax' : None }

        zscale = kwargs.get('zscale','lin')
        gamma = kwargs.get('gamma',0.5)
        beam_size = kwargs.get('beam_size',None)
        
        if zscale == 'pow':
            kwargs_imshow['norm'] = PowerNorm(gamma=gamma)
        elif zscale == 'sqrt': 
            kwargs_imshow['norm'] = PowerNorm(gamma=0.5)
        elif zscale == 'log': kwargs_imshow['norm'] = LogNorm()
        elif zscale == 'lin': kwargs_imshow['norm'] = Normalize()
        else: kwargs_imshow['norm'] = Normalize()
        
        ax = pywcsgrid2.subplot(subplot, header=self._wcs.to_header())
#        ax = pywcsgrid2.axes(header=self._wcs.to_header())

        load_ds9_cmap()
        colormap = mpl.cm.get_cmap(cmap)
        colormap.set_under('white')

        data = copy.copy(self._data)
        kwargs_imshow = merge_dict(kwargs_imshow,kwargs)
        kwargs_contour = merge_dict(kwargs_contour,kwargs)
        
        im = ax.imshow(data.T,**kwargs_imshow)
        im.set_cmap(colormap)

        if kwargs_contour['levels']:        
            cs = ax.contour(data.T,**kwargs_contour)
        #        plt.clabel(cs, fontsize=5, inline=0)
        
#        im.set_clim(vmin=np.min(self._counts[~self._roi_msk]),
#                    vmax=np.max(self._counts[~self._roi_msk]))
        
        ax.set_ticklabel_type("d", "d")

#        if self._axes[0]._coordsys == 'gal':
#            ax.set_xlabel('GLON')
#            ax.set_ylabel('GLAT')
#        else:        
        ax.set_xlabel('RA')
        ax.set_ylabel('DEC')

        xlabel = kwargs.get('xlabel',None)
        ylabel = kwargs.get('ylabel',None)
        if xlabel is not None: ax.set_xlabel(xlabel)
        if ylabel is not None: ax.set_ylabel(ylabel)

#        plt.colorbar(im,orientation='horizontal',shrink=0.7,pad=0.15,
#                     fraction=0.05)
        ax.grid()
        
#        ax.add_compass(loc=1)
#        ax.set_display_coord_system("gal")       
 #       ax.locator_params(axis="x", nbins=12)

#        ax.add_size_bar(1./self._axes[0]._delta, # 30' in in pixel
#                        r"$1^{\circ}$",loc=3,color='w')
            
        if beam_size is not None:
            ax.add_beam_size(2.0*beam_size[0]/self._axes[0]._delta,
                             2.0*beam_size[1]/self._axes[1]._delta,
                             beam_size[2],beam_size[3],
                             patch_props={'fc' : "none", 'ec' : "w"})
            
#        self._ax = ax
        
        return im, ax

class ROIPlotter(AnalysisBase):

    defaults = {
        'marker_threshold' : (10,''),
        'source_color'     : ('w','')
        }
    
    def __init__(self,fitsfile,roi,**kwargs):
        AnalysisBase.__init__(self,None,**kwargs)
        
        self._implot = ImagePlotter(fitsfile)
        self._roi = roi

    def plot(self,**kwargs):

#        ax = kwargs.get('ax',plt.gca())

        
        
        marker_threshold = 10
        label_threshold = 10
        src_color='w'
        fontweight = 'normal'
        
        im_kwargs = dict(cmap='ds9_b',vmin=None,vmax=None,levels=None,
                         zscale='lin',subplot=111)
        
        plot_kwargs = dict(linestyle='None',marker='+',
                           markerfacecolor = 'None',
                           markeredgecolor=src_color,clip_on=True)
        
        text_kwargs = dict(color=src_color,size=8,clip_on=True,
                           fontweight='normal')

        cb_kwargs = dict(orientation='vertical',shrink=1.0,pad=0.1,
                         fraction=0.1,cb_label=None)
        
        
        im_kwargs = merge_dict(im_kwargs,kwargs,add_new_keys=True)
        plot_kwargs = merge_dict(plot_kwargs,kwargs)
        text_kwargs = merge_dict(text_kwargs,kwargs)
        cb_kwargs = merge_dict(cb_kwargs,kwargs)
                
        im, ax = self._implot.plot(**im_kwargs)
        pixcrd = self._implot._wcs.wcs_world2pix(self._roi._src_skydir.ra.deg,
                                           self._roi._src_skydir.dec.deg,0)
        
        for i, s in enumerate(self._roi.sources):

            label = s.name
            ax.text(pixcrd[0][i]+2.0,pixcrd[1][i]+2.0,label,
                    **text_kwargs)

    #        if marker_threshold is not None and s['Signif_Avg'] > marker_threshold:      
            ax.plot(pixcrd[0][i],pixcrd[1][i],**plot_kwargs)

        extent = im.get_extent()
        ax.set_xlim(extent[0],extent[1])
        ax.set_ylim(extent[2],extent[3])

        cb_label = cb_kwargs.pop('cb_label',None)
        cb = plt.colorbar(im,**cb_kwargs)
        if cb_label: cb.set_label(cb_label)
        
