from datetime import datetime
import numpy as np
from netcdf import netcdf as nc
import logging
from linketurbidity import instrument as linke
from noaadem import instrument as dem


class Cache(object):

    def __init__(self):
        self._attrs = {}

    def __getattr__(self, name):
        if name not in self._attrs.keys():
            var_name = name[4:] if name[0:4] == 'ref_' else name
            if 'ref_%s' % var_name not in self._attrs.keys():
                var = nc.getvar(self.root, var_name)
                self._attrs['ref_%s' % var_name] = var
            else:
                var = self._attrs
            self._attrs[var_name] = var[:]
        return self._attrs[name]

    def dump(self):
        for k in self._attrs.keys():
            self._attrs.pop(k, None)
        nc.close(self.root)


class StaticCacheConstructor(object):

    def __init__(self, filenames, tile_cut={}):
        # At first it should have: lat, lon, dem, linke
        self.root, is_new = nc.open('static.nc')
        if is_new:
            logging.info("This is the first execution from the deployment... ")
            with nc.loader(filenames[0]) as root_ref:
                self.lat = nc.getvar(root_ref, 'lat')
                self.lon = nc.getvar(root_ref, 'lon')
                nc.getvar(self.root, 'lat', source=self.lat)
                nc.getvar(self.root, 'lon', source=self.lon)
                self.project_dem()
                self.project_linke()
                nc.sync(self.root)
        self.root = nc.tailor(self.root, dimensions=tile_cut)

    def project_dem(self):
        logging.info("Projecting DEM's map... ")
        dem_var = nc.getvar(self.root, 'dem', 'f4', source=self.lon)
        dem_var[:] = dem.obtain(self.lat[0], self.lon[0])

    def project_linke(self):
        logging.info("Projecting Linke's turbidity index... ")
        dts = map(lambda m: datetime(2014, m, 15), range(1, 13))
        linkes = map(lambda dt: linke.obtain(dt, compressed=True), dts)
        linkes = map(lambda l: linke.transform_data(l, self.lat[0],
                                                    self.lon[0]), linkes)
        linkes = np.vstack([[linkes]])
        nc.getdim(self.root, 'months', 12)
        linke_var = nc.getvar(self.root, 'linke', 'f4', ('months', 'yc', 'xc'))
        # The linkes / 20. uncompress the linke coefficients and save them as
        # floats.
        linke_var[:] = linkes / 20.


class Loader(Cache):

    def __init__(self, filenames, tile_cut={}, read_only=False):
        super(Loader, self).__init__()
        self.filenames = filenames
        self.root = nc.tailor(filenames, dimensions=tile_cut,
                              read_only=read_only)
        self.static = StaticCacheConstructor(filenames, tile_cut)
        self.static_cached = self.static.root

    @property
    def dem(self):
        if not hasattr(self, '_cached_dem'):
            self._cached_dem = nc.getvar(self.static_cached, 'dem')[:]
        return self._cached_dem

    @property
    def linke(self):
        if not hasattr(self, '_linke'):
            self._linke = nc.getvar(self.static_cached, 'linke')[:]
        return self._linke

    @property
    def calibrated_data(self):
        if not hasattr(self, '_cached_calibrated_data'):
            row_data = self.data[:]
            counts_shift = self.counts_shift[:]
            space_measurement = self.space_measurement[:]
            prelaunch = self.prelaunch_0[:]
            postlaunch = self.postlaunch[:]
            # INFO: Without the postlaunch coefficient the RMSE go to 15%
            normalized_data = (np.float32(row_data) / counts_shift -
                               space_measurement)
            self._cached_calibrated_data = (normalized_data
                                            * postlaunch
                                            * prelaunch)
        return self._cached_calibrated_data


class memoize(object):

    def __init__(self, function):
        self.function = function
        self.memoized = {}

    def __call__(self, *args):
        try:
            return self.memoized[args]
        except KeyError:
            self.memoized[args] = self.function(*args)
        return self.memoized[args]
