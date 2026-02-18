# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# This file provides the contraact for our Strategy and Command design pattern
# We use strategy pattern to provide a unified interface to each of  our image tweaking operations  
# We use Command pattern to place each slider move and laye rresize onto the undo stack   

# THIS FILE IS ALSO THE SINGLE SOURCE OF TRUTH FOR APPNAME AND APP VERSION  

# ######################################################################################

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from enum import Enum

APP_NAME = "PhotoGlimmer" #this is the name all loggers will use 
APP_VERSION= "0.9.6"

 
class StrategyScope(str, Enum):
    """ Merely to tell user the  scope. has no effect on actual execution """
    FACE = "face"
    LAYER = "layer"
    GLOBAL = "global"


# ###################################################################
# If you are creating a strategy, implement this abstract class 
# The UI  for controlling your function parameters will be automagically created 
# Look at strategies.py for guidance 
# ###################################################################
class AdjustmentStrategy(ABC):
    """
    Interface for image processing algorithms.
    Implementing this allows the engine to apply filters (Brightness, Slimming, etc.)
    without knowing the internal math of the filter.    
    """

    # Define Scope    
    iSGlobal:bool = 'False'
    # an enum for hinting the user, if ui so chooses.  May not be used in algorithm at all    
    scope: StrategyScope = StrategyScope.LAYER
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, tuple]: 
        """Returns {param_name: (min, max, default)} for UI generation."""
        pass
    
    
    
    def apply(self, patch: np.ndarray, 
              mask: np.ndarray, 
              params: Dict[str, float], scale: float, 
              cache: Optional[Dict] = None,
                *args, **kwargs) -> np.ndarray: 
        """
        Processes the image patch. 
        'scale' is used to adjust pixel-based values (like blur radius) 
        so they look identical on proxy vs high-res.
        'cache' is a dictionary for lazy-loading heavy resources (like AI masks).
        """
        pass



class SegmenterStrategy(ABC):
    """
    Interface for AI Segmentation engines (MediaPipe, SAM).
    Separating this allows swapping AI models without changing the ImageSession.
    """
    @abstractmethod
    def segment(self, patch: np.ndarray, params: Dict[str, Any]) -> np.ndarray: 
        """Returns a 2D grayscale numpy array (0-255)."""
        pass
        

# ###################################################################
# Abstract Interface for command design pattern
# ##################################################################



class Command(ABC):
    @abstractmethod
    def execute(self): pass
    @abstractmethod
    def undo(self): pass

