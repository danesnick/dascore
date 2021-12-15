"""
A 2D trace object.
"""
from typing import Mapping, Optional, Tuple, Union

import numpy as np
from numpy.typing import ArrayLike
from xarray import DataArray

import dascore.proc
from dascore.constants import COMPARE_ATTRS, PatchType
from dascore.io import PatchIO
from dascore.transform import TransformPatchNameSpace
from dascore.utils.mapping import FrozenDict
from dascore.utils.patch import Coords, _AttrsCoordsMixer
from dascore.viz import VizPatchNameSpace


class Patch:
    """
    A Class for storing and accessing 2D fiber data.
    """

    # --- Dunder methods

    def __init__(
        self,
        data: Union[ArrayLike, DataArray] = None,
        coords: Mapping[str, ArrayLike] = None,
        dims: Tuple[str] = None,
        attrs: Optional[Mapping] = None,
    ):
        if isinstance(data, DataArray):
            self._data_array = data
            return
        dims = dims if dims is not None else list(coords)
        mixer = _AttrsCoordsMixer(attrs, coords, dims)
        attrs, coords = mixer()
        # get xarray coords from custom coords object
        if isinstance(coords, Coords):
            coords = coords._coords
        self._data_array = DataArray(data=data, dims=dims, coords=coords, attrs=attrs)

    def __eq__(self, other):
        """
        Compare one Trace2D to another.

        Parameters
        ----------
        other

        Returns
        -------

        """
        return self.equals(other)

    def __str__(self):
        xarray_str = str(self._data_array)
        class_name = self.__class__.__name__
        return xarray_str.replace("xarray.DataArray", f"dascore.{class_name}")

    __repr__ = __str__

    def equals(self, other: PatchType, only_required_attrs=True) -> bool:
        """
        Determine if the current trace equals the other trace.

        Parameters
        ----------
        other
            A Trace2D object
        only_required_attrs
            If True, only compare required attributes.
        """

        if only_required_attrs:
            attrs1 = {k: v for k, v in self.attrs.items() if k in COMPARE_ATTRS}
            attrs2 = {k: v for k, v in other.attrs.items() if k in COMPARE_ATTRS}
        else:
            attrs1, attrs2 = dict(self.attrs), dict(other.attrs)
        if attrs1 != attrs2:
            return False
        return np.equal(self.data, other.data).all()

    def new(self: PatchType, data=None, coords=None, attrs=None) -> PatchType:
        """
        Return a copy of the trace with data, coords, or attrs updated.
        """
        data = data if data is not None else self.data
        attrs = attrs if attrs is not None else self.attrs
        if coords is None:
            coords = getattr(self.coords, "_coords", self.coords)
        return self.__class__(data=data, coords=coords, attrs=attrs)

    def update_attrs(self: PatchType, **attrs) -> PatchType:
        """
        Update attrs and return a new Patch.

        Parameters
        ----------
        **attrs
            attrs to add/update.
        """
        dar = self._data_array
        mixer = _AttrsCoordsMixer(dar.attrs, dar.coords, dar.dims)
        mixer.update_attrs(**attrs)
        attrs, coords = mixer()
        return self.__class__(self.data, coords=coords, attrs=attrs)

    @property
    def iloc(self):
        """Return an index locator for selecting based on index, not values."""

    @property
    def data(self):
        """Return the data array."""
        return self._data_array.data

    @property
    def coords(self):
        """Return the data array."""
        return Coords(self._data_array.coords)

    @property
    def dims(self) -> Tuple[str, ...]:
        """Return the data array."""
        return self._data_array.dims

    @property
    def attrs(self) -> FrozenDict:
        """Return the attributes of the trace."""
        return FrozenDict(self._data_array.attrs)

    squeeze = dascore.proc.squeeze
    rename = dascore.proc.rename
    transpose = dascore.proc.transpose

    # --- processing funcs

    select = dascore.proc.select
    decimate = dascore.proc.decimate
    detrend = dascore.proc.detrend
    pass_filter = dascore.proc.pass_filter
    aggregate = dascore.proc.aggregate
    abs = dascore.proc.abs

    # --- Method Namespaces
    # Note: these can't be cached_property (from functools) or references
    # to self stick around and keep large arrays in memory.

    @property
    def viz(self) -> VizPatchNameSpace:
        """The visualization namespace."""
        return VizPatchNameSpace(self)

    @property
    def tran(self) -> TransformPatchNameSpace:
        """The transformation namespace."""
        return TransformPatchNameSpace(self)

    @property
    def io(self) -> PatchIO:
        """Return a patch IO object for saving patches to various formats."""
        return PatchIO(self)
