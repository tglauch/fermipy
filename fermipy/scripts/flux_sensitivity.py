# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function

import os
import argparse

import pyLikelihood as pyLike

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table, Column
from astropy.io import fits

from fermipy import utils
from fermipy import spectrum
from fermipy import irfs
from fermipy import skymap
from fermipy.ltcube import LTCube
from fermipy.sensitivity import SensitivityCalc
from fermipy.hpx_utils import HPX
from fermipy.skymap import HpxMap


def main(args=None):
    usage = "usage: %(prog)s [options]"
    description = "Calculate the LAT point-source flux sensitivity."
    parser = argparse.ArgumentParser(usage=usage, description=description)

    parser.add_argument('--ltcube', default=None,
                        help='Set the path to the livetime cube.')
    parser.add_argument('--galdiff', default=None, required=True,
                        help='Set the path to the galactic diffuse model.')
    parser.add_argument('--isodiff', default=None,
                        help='Set the path to the isotropic model.  If none then the '
                        'default model will be used for the given event class.')

    parser.add_argument('--galdiff_fit', default=None,
                        help='Set the path to the galactic diffuse model used for fitting. '
                        'This can be used to assess the impact of IEM systematics  '
                        'from fitting with the wrong model.  If none '
                        'then the same model will be used for data and fit.')
    
    parser.add_argument('--isodiff_fit', default=None,
                        help='Set the path to the isotropic model used for fitting.  '
                        'This can be used to assess the impact of IEM systematics  '
                        'from fitting with the wrong model.  If none '
                        'then the same model will be used for data and fit.')
    
    parser.add_argument('--ts_thresh', default=25.0, type=float,
                        help='Set the detection threshold.')
    parser.add_argument('--min_counts', default=3.0, type=float,
                        help='Set the minimum number of counts.')
    parser.add_argument('--event_class', default='P8R2_SOURCE_V6',
                        help='Set the IRF name (e.g. P8R2_SOURCE_V6).')
    parser.add_argument('--glon', default=0.0, type=float,
                        help='Galactic longitude.')
    parser.add_argument('--glat', default=0.0, type=float,
                        help='Galactic latitude.')
    parser.add_argument('--index', default=2.0, type=float,
                        help='Source power-law index.')
    parser.add_argument('--emin', default=10**1.5, type=float,
                        help='Minimum energy in MeV.')
    parser.add_argument('--emax', default=10**6.0, type=float,
                        help='Maximum energy in MeV.')
    parser.add_argument('--nbin', default=18, type=int,
                        help='Number of energy bins for differential flux calculation.')
    parser.add_argument('--nside', default=None, type=int,
                        help='Set the NSIDE parameter of the all-sky sensivity map.  If None then no sensitivity maps '
                        'will be computed.  WARNING: Running with a large nside parameter is very '
                        'computationally and memory intensive.')
    parser.add_argument('--output', default='output.fits', type=str,
                        help='Output filename.')
    parser.add_argument('--obs_time_yr', default=None, type=float,
                        help='Rescale the livetime cube to this observation time in years.  If none then the '
                        'calculation will use the intrinsic observation time of the livetime cube.')

    args = parser.parse_args(args)
    run_flux_sensitivity(**vars(args))


def run_flux_sensitivity(**kwargs):

    index = kwargs.get('index', 2.0)
    emin = kwargs.get('emin', 10**1.5)
    emax = kwargs.get('emax', 10**6.0)
    nbin = kwargs.get('nbin', 18)
    glon = kwargs.get('glon', 0.0)
    glat = kwargs.get('glat', 0.0)
    ltcube_filepath = kwargs.get('ltcube', None)
    galdiff_filepath = kwargs.get('galdiff', None)
    isodiff_filepath = kwargs.get('isodiff', None)
    galdiff_fit_filepath = kwargs.get('galdiff_fit', None)
    isodiff_fit_filepath = kwargs.get('isodiff_fit', None)
    
    obs_time_yr = kwargs.get('obs_time_yr', None)
    event_class = kwargs.get('event_class', 'P8R2_SOURCE_V6')
    min_counts = kwargs.get('min_counts', 3.0)
    ts_thresh = kwargs.get('ts_thresh', 25.0)
    nside = kwargs.get('nside', None)
    output = kwargs.get('output', None)

    event_types = [['FRONT', 'BACK']]
    fn = spectrum.PowerLaw([1E-13, -index], scale=1E3)

    log_ebins = np.linspace(np.log10(emin),
                            np.log10(emax), nbin + 1)
    ebins = 10**log_ebins
    ectr = np.exp(utils.edge_to_center(np.log(ebins)))

    c = SkyCoord(glon, glat, unit='deg', frame='galactic')

    if ltcube_filepath is None:

        if obs_time_yr is None:
            raise Exception('No observation time defined.')

        ltc = LTCube.create_from_obs_time(obs_time_yr * 365 * 24 * 3600.)
    else:
        ltc = LTCube.create(ltcube_filepath)
        if obs_time_yr is not None:
            ltc._counts *= obs_time_yr * 365 * \
                24 * 3600. / (ltc.tstop - ltc.tstart)

    gdiff = skymap.Map.create_from_fits(galdiff_filepath)
    gdiff_fit = None
    if galdiff_fit_filepath is not None:
        gdiff_fit = skymap.Map.create_from_fits(galdiff_fit_filepath)
        
    if isodiff_filepath is None:
        isodiff = utils.resolve_file_path('iso_%s_v06.txt' % event_class,
                                          search_dirs=[os.path.join('$FERMIPY_ROOT', 'data'),
                                                       '$FERMI_DIFFUSE_DIR'])
        isodiff = os.path.expandvars(isodiff)
    else:
        isodiff = isodiff_filepath


    iso = np.loadtxt(isodiff, unpack=True)
    iso_fit = None
    if isodiff_fit_filepath is not None:
        iso_fit = np.loadtxt(isodiff_fit_filepath, unpack=True)
    
    scalc = SensitivityCalc(gdiff, iso, ltc, ebins,
                            event_class, event_types, gdiff_fit=gdiff_fit,
                            iso_fit=iso_fit)

    # Compute Maps
    map_diff_flux = None
    map_diff_npred = None
    map_int_flux = None
    map_int_npred = None
    
    if nside is not None:

        hpx = HPX(nside, True, 'GAL', ebins=ebins)
        map_diff_flux = HpxMap(np.zeros((nbin,hpx.npix)),hpx)
        map_diff_npred = HpxMap(np.zeros((nbin,hpx.npix)),hpx)
        map_skydir = map_diff_flux.hpx.get_sky_dirs()

        o = scalc.diff_flux_threshold(map_skydir, fn, ts_thresh, min_counts)
        map_diff_flux.data[...] = o['flux'].T
        map_diff_npred.data[...] = o['npred'].T

        hpx = HPX(nside, True, 'GAL')
        map_int_flux = HpxMap(np.zeros((hpx.npix)),hpx)
        map_int_npred = HpxMap(np.zeros((hpx.npix)),hpx)
        map_skydir = map_int_flux.hpx.get_sky_dirs()

        o = scalc.int_flux_threshold(map_skydir, fn, ts_thresh, min_counts)
        map_int_flux.data[...] = o['flux']
        map_int_npred.data[...] = o['npred']
        
    o = scalc.diff_flux_threshold(c, fn, ts_thresh, min_counts)
        
    cols = [Column(name='e_min', dtype='f8', data=scalc.ebins[:-1], unit='MeV'),
            Column(name='e_ref', dtype='f8', data=o['e_ref'], unit='MeV'),
            Column(name='e_max', dtype='f8', data=scalc.ebins[1:], unit='MeV'),
            Column(name='flux', dtype='f8', data=o[
                   'flux'], unit='ph / (cm2 s)'),
            Column(name='eflux', dtype='f8', data=o[
                   'eflux'], unit='MeV / (cm2 s)'),
            Column(name='dnde', dtype='f8', data=o['dnde'],
                   unit='ph / (MeV cm2 s)'),
            Column(name='e2dnde', dtype='f8',
                   data=o['e2dnde'], unit='MeV / (cm2 s)'),
            Column(name='npred', dtype='f8', data=o['npred'], unit='ph')]

    tab_diff = Table(cols)

    cols = [Column(name='index', dtype='f8'),
            Column(name='e_min', dtype='f8', unit='MeV'),
            Column(name='e_ref', dtype='f8', unit='MeV'),
            Column(name='e_max', dtype='f8', unit='MeV'),
            Column(name='flux', dtype='f8', unit='ph / (cm2 s)'),
            Column(name='eflux', dtype='f8', unit='MeV / (cm2 s)'),
            Column(name='dnde', dtype='f8', unit='ph / (MeV cm2 s)'),
            Column(name='e2dnde', dtype='f8', unit='MeV / (cm2 s)'),
            Column(name='npred', dtype='f8', unit='ph')]

    cols_ebin = [Column(name='index', dtype='f8'),
                 Column(name='e_min', dtype='f8',
                        unit='MeV', shape=(len(ectr),)),
                 Column(name='e_ref', dtype='f8',
                        unit='MeV', shape=(len(ectr),)),
                 Column(name='e_max', dtype='f8',
                        unit='MeV', shape=(len(ectr),)),
                 Column(name='flux', dtype='f8',
                        unit='ph / (cm2 s)', shape=(len(ectr),)),
                 Column(name='eflux', dtype='f8',
                        unit='MeV / (cm2 s)', shape=(len(ectr),)),
                 Column(name='dnde', dtype='f8',
                        unit='ph / (MeV cm2 s)', shape=(len(ectr),)),
                 Column(name='e2dnde', dtype='f8',
                        unit='MeV / (cm2 s)', shape=(len(ectr),)),
                 Column(name='npred', dtype='f8', unit='ph', shape=(len(ectr),))]

    tab_int = Table(cols)
    tab_int_ebin = Table(cols_ebin)

    index = np.linspace(1.0, 5.0, 4 * 4 + 1)

    for g in index:
        fn = spectrum.PowerLaw([1E-13, -g], scale=10**3.5)
        o = scalc.int_flux_threshold(c, fn, ts_thresh, 3.0)
        row = [g]
        for colname in tab_int.columns:
            if not colname in o:
                continue
            row += [o[colname]]

        tab_int.add_row(row)

        row = [g]
        for colname in tab_int.columns:
            if not colname in o:
                continue
            row += [o['bins'][colname]]
        tab_int_ebin.add_row(row)

    hdulist = fits.HDUList()
    hdulist.append(fits.table_to_hdu(tab_diff))
    hdulist.append(fits.table_to_hdu(tab_int))
    hdulist.append(fits.table_to_hdu(tab_int_ebin))

    hdulist[1].name = 'DIFF_FLUX'
    hdulist[2].name = 'INT_FLUX'
    hdulist[3].name = 'INT_FLUX_EBIN'

    if nside is not None:
        hdu = map_diff_flux.create_image_hdu()
        hdu.name = 'MAP_DIFF_FLUX'
        hdulist.append(hdu)
        hdu = map_diff_npred.create_image_hdu()
        hdu.name = 'MAP_DIFF_NPRED'
        hdulist.append(hdu)

        hdu = map_int_flux.create_image_hdu()
        hdu.name = 'MAP_INT_FLUX'
        hdulist.append(hdu)
        hdu = map_int_npred.create_image_hdu()
        hdu.name = 'MAP_INT_NPRED'
        hdulist.append(hdu)
        
    hdulist.writeto(output, clobber=True)

if __name__ == "__main__":
    main()
