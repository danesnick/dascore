"""
A module for storing streams of fiber data.
"""
import abc
from typing import Optional, Sequence, Union
from typing_extensions import Self

import pandas as pd

import dascore
from dascore.constants import PatchType, SpoolType, timeable_types, numeric_types
from dascore.utils.docs import compose_docstring
from dascore.utils.patch import merge_patches, scan_patches
from dascore.utils.pd import filter_df
from dascore.utils.chunk import chunk


class BaseSpool(abc.ABC):
    """
    Spool Abstract Base Class (ABC) for defining Spool interface.
    """

    @abc.abstractmethod
    def __getitem__(self, item: int) -> PatchType:
        """Returns a patch from the spool."""

    @abc.abstractmethod
    def __iter__(self) -> PatchType:
        """Iterate through the Patches in the spool."""

    def update(self: SpoolType) -> Self:
        """
        Updates the contents of the spool and returns a spool.
        """
        return self

    @abc.abstractmethod
    def chunk(
        self: SpoolType,
        overlap: Optional[Union[numeric_types, timeable_types]] = None,
        keep_partial: bool = False,
        **kwargs
    ) -> Self:
        """
        Chunk the data in the spool along specified dimensions.

        Parameters
        ----------
        overlap
            The amount of overlap for each chunk
        keep_partial
            If True, keep the segments which are smaller than chunk size.
            This often occurs because of data gaps or at end of chunks.
        kwargs
            kwargs are used to specify the dimension along which to chunk, eg:
            `time=10` chunks along the time axis in 10 second increments.
        """

    @abc.abstractmethod
    def select(self: SpoolType, **kwargs) -> Self:
        """
        Select only part of the data.
        """

    @abc.abstractmethod
    def get_contents(self: SpoolType, **kwargs) -> pd.DataFrame:
        """
        Get a dataframe of the patches in spool.

        Can be filtered using kwargs. For example:
            get_contents(time=('2012-01-01', None))
        Will only return a dataframe of patches which contain data after
        the specified minimum value for time.
        """


class DataFrameSpool(BaseSpool):
    """A spool whose contents are managed by a dataframe."""

    # A dataframe which represents contents as they will be output
    _df: Optional[pd.DataFrame] = None
    # A dataframe which shows patches in the source
    _source_df: Optional[pd.DataFrame] = None
    # A dataframe of instructions for going from source_df to df
    _instruction_df: Optional[pd.DataFrame] = None

    def __getitem__(self, item):
        return self.load_patch(self._df.iloc[0])

    def __len__(self):
        return len(self._df)

    def __iter__(self):
        for ind in range(len(self._df)):
            yield self.load_patch(self._df.iloc[ind])

    @abc.abstractmethod
    def _extract_patch_from_row(self, row) -> PatchType:
        """Given a row from the managed dataframe, return a patch."""

    def load_patch(self, row):
        """
        Load a patch from a row of the dataframe.
        """
        patch = self._extract_patch_from_row(row)
        return patch

    @compose_docstring(doc=BaseSpool.chunk.__doc__)
    def chunk(
        self: SpoolType,
        overlap: Optional[Union[numeric_types, timeable_types]] = None,
        keep_partial: bool = False,
        **kwargs
    ) -> Self:
        """
        {doc}
        """
        df = self._df
        out, instructions = chunk(
            df, overlap=overlap, keep_partial=keep_partial, **kwargs
        )
        return self.new_from_df(out, source_df=df, instruction_df=instructions)

    @classmethod
    def new_from_df(cls, df, source_df=None, instruction_df=None):
        """Create a new instance from dataframes."""
        new = cls()
        new._df = df
        new._source_df = source_df if source_df is not None else df
        new._instruction_df = instruction_df
        return new

    def select(self, **kwargs) -> Self:
        """Sub-select certain dimensions for Spool"""

    @compose_docstring(doc=BaseSpool.get_contents.__doc__)
    def get_contents(self, **kwargs) -> pd.DataFrame:
        """
        {doc}
        """
        return self._df[filter_df(self._df, **kwargs)]


class MemorySpool(DataFrameSpool):
    """
    A Spool for storing patches in memory.
    """

    # a tuple of attrs that must be compatible for patches to be merged
    _merge_attrs = ("network", "station", "dims", "data_type", "category")

    # tuple of attributes to remove from table

    def __init__(self, data: Union[PatchType, Sequence[PatchType]]):
        self._df = self._get_patch_table(data)

    @compose_docstring(doc=BaseSpool.chunk.__doc__)
    def chunk(
        self: SpoolType,
        overlap: Optional[Union[numeric_types, timeable_types]] = None,
        keep_partial: bool = False,
        **kwargs
    ) -> SpoolType:
        """{doc}"""

    def _get_patch_table(self, patch_iterable: Sequence[PatchType]) -> pd.DataFrame:
        """
        Create a table with metadata about patches.
        """
        if isinstance(patch_iterable, dascore.Patch):
            patch_iterable = [patch_iterable]
        df = pd.DataFrame(scan_patches(patch_iterable))
        df["patch"] = patch_iterable
        return df

    def merge(self, dim="time"):
        """
        Merge all compatible patches in stream together.

        Parameters
        ----------
        dim
            dimension along which to try to merge.

        See also :func:`dascore.utils.patch.merge_patches`
        """
        new_patches = merge_patches(self._df, dim=dim)
        return self.__class__(new_patches)

    def _extract_patch_from_row(self, row):
        """Load the patch into memory"""
        return row["patch"]
