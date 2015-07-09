
import fermipy

#def build_defaults():
#    path = os.path.join(fermipy.PACKAGE_ROOT,'config','defaults.yaml')
#    with open(path,'r') as f: config = yaml.load(f)

# Options for defining input data files
data = {
    'evfile'    : (None,'Input FT1 file.'),
    'scfile'    : (None,'Input FT2 file.'),
    'ltcube'    : (None,'Input LT cube file (optional).'),
    }

# Options for data selection.
selection = {
    'emin'    : (None,'Minimum Energy'),
    'emax'    : (None,'Maximum Energy'),
    'tmin'    : (None,'Minimum time (MET).'),
    'tmax'    : (None,'Maximum time (MET).'),
    'zmax'    : (None,'Maximum zenith angle.'),
    'evclass' : (None,'Event class selection.'),
    'evtype'  : (None,'Event type selection.'),
    'convtype': (None,'Conversion type selection.'),
    'target'  : (None,'Choose an object name that will define the center of the ROI.  '
                 'This option takes precendence over ra/dec.'),
    'ra'      : (None,''),
    'dec'     : (None,''),
    'glat'    : (None,''),
    'glon'    : (None,''),
    'radius'  : (None,''),
    'filter'  : ('DATA_QUAL>0 && LAT_CONFIG==1',''),
    'roicut'  : ('no','')
    }

# Options for ROI model.
model = {
    'src_radius'        :
        (None,'Set the maximum distance for inclusion of sources in the ROI '
         'model.  Selects all sources within a circle of this radius centered '
         'on the ROI.  If none then no selection is applied.  This selection '
         'will be ORed with sources passing the cut on src_roiwidth.'),
    'src_roiwidth'        :
        (None,'Select sources within a box of RxR centered on the ROI.  If '
         'none then no cut is applied.'),    
    'isodiff'       : (None,'Set the isotropic template.'),
    'galdiff'       : (None,'Set the galactic IEM mapcube.'),
    'limbdiff'      : (None,''),
    'sources'       : (None,'',list),
    'extdir'        : ('Extended_archive_v14',''),
    'catalogs'      : (None,'',list),
    'min_ts'        : (None,''),
    'min_flux'      : (None,''),
    'remove_duplicates' : (False,'Remove duplicate catalog sources.')
    }

# Options for configuring likelihood analysis
gtlike = {
    'irfs'          : (None,''),
    'edisp'         : (True,''),
    'edisp_disable' : (None,'Provide a list of sources for which the edisp correction should be disabled.',list),
    'likelihood'    : ('binned','')
    }

# Options for binning.
binning = {
    'proj'       : ('AIT',''),
    'coordsys'   : ('CEL',''),        
    'npix'       : 
    (None,
     'Number of spatial bins.  If none this will be inferred from roiwidth '
     'and binsz.'), 
    'roiwidth'  : (10.0,'Set the width of the ROI in degrees.  If both roiwidth and binsz are '
                    'given the roiwidth will be rounded up to be a multiple of binsz.'),
    'binsz'      : (0.1,'Set the bin size in degrees.'),
    'binsperdec' : (8,'Set the number of energy bins per decade.'),
    'enumbins'   : (None,'Number of energy bins.  If none this will be inferred from energy '
                    'range and binsperdec.')
    }

# Options related to I/O and output file bookkeeping
fileio = {
    'outdir'       : (None,'Set the name of the output directory.'),
    'scratchdir'   : ('/scratch',''),
    'workdir'      : (None,'Override the working directory.'),
    'logfile'      : (None,''),
    'saveoutput'   : (True,'Save intermediate FITS data products.'),
    'stageoutput'  : 
    (True,'Stage output to an intermediate working directory.'),
    }

logging = {
    'chatter'     : (3,'Set the chatter parameter of the STs.'),
    'verbosity'   : (3,'')
    }

# Options related to likelihood optimizer
optimizer = {
    'optimizer'   : 
    ('MINUIT','Set the optimization algorithm to use when maximizing the '
     'likelihood function.'),
    'tol'              : (1E-4,'Set the optimizer tolerance.'),
    'retries'          : (3,'Set the number of times to retry the fit.'),
    'min_fit_quality'  : (3,'Set the minimum fit quality.'),
    'verbosity'        : (0,'')
    }

# MC options
mc = { }

#
roiopt = {
    'free_source_radius'       : (None,''),
    'free_source_roi_margin'   : (None,''),
    'free_sources'             : (None,''),
    'free_source_ts_threshold' : (None,'')
    }

#
residmap = {
    'models'                   : (None,'',list),
    }
