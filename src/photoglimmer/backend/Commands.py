# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ######################################################################################
# Part of the Command Pattern
# Any operation that needs to support undo/redo must encauslate itself as a command  
# Each command must implement execute and undo 
# This file has the concrete implementations of Commnads we will need 
# YOU DON'T NEED TO DEAL WITH THESE IF YOU ARE ADDING A NEW STRATEGY  
# ANY SLIDER CHANGE WILL BE ADDED OT UNDO STACK AUTOMATICALLY AS IT WILL BR ROUTED 
# THROUGH UpdateParamCommand BELOW
# ######################################################################################


from .Interfaces import Command

# fOR type hinting support :
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ImageSession import ImageSession, Layer



class UpdateParamCommand(Command):
    """ encapsulates Whenever a slider is moved   """
    #TODO :  maybe get layer_id from layer itself
    def __init__(self, layer_id, layer, strat_key, param_key, old_val, new_val):
        self.layer_id = layer_id  # Store the ID explicitly
        self.layer = layer
        self.strat_key = strat_key
        self.param_key = param_key
        self.old_val = old_val
        self.new_val = new_val

    def execute(self):
        if self.strat_key not in self.layer.state.adjustments:
            self.layer.state.adjustments[self.strat_key] = {}
        self.layer.state.adjustments[self.strat_key][self.param_key] = self.new_val

    def undo(self):
        self.layer.state.adjustments[self.strat_key][self.param_key] = self.old_val

    def __str__(self):
        return f"Layer {self.layer_id}: {self.param_key} [{self.old_val} -> {self.new_val}]"
    


class UpdateMaskParamCommand(Command):
    def __init__(self, session, layer, param_key, old_val, new_val):
        self.session, self.layer, self.param_key = session, layer, param_key
        self.old_val, self.new_val = old_val, new_val
    def execute(self):
        self.layer.state.adjustments[self.param_key] = self.new_val
        self.session._generate_layer_mask(self.layer.id)
    def undo(self):
        self.layer.state.adjustments[self.param_key] = self.old_val
        self.session._generate_layer_mask(self.layer.id)



class UpdatePropertyCommand(Command):
    """Updates core layer properties (opacity, strength, feather). """
    def __init__(self, layer_id, layer, prop_name, old_val, new_val):
        self.layer_id = layer_id
        self.layer = layer
        self.prop_name = prop_name
        self.old_val = old_val
        self.new_val = new_val

    def execute(self):
        setattr(self.layer.state, self.prop_name, self.new_val)

    def undo(self):
        setattr(self.layer.state, self.prop_name, self.old_val)

    def __str__(self):
        return f"Layer {self.layer_id}: {self.prop_name} [{self.old_val} -> {self.new_val}]"
    



class UpdateGeometryCommand(Command):
    """Layer resize and move """
    def __init__(self, session, layer_id, old_bounds, new_bounds, old_mask):
        self.session = session
        self.layer_id = layer_id
        self.old_bounds = old_bounds
        self.new_bounds = new_bounds
        self.old_mask = old_mask # We save the mask to avoid re-running AI on Undo

    def execute(self):
        # We don't need to do anything here because the session method 
        # has already applied the "new" state before pushing this command.
        # But if we were Redoing, we would apply new_bounds.
        self.session._apply_geometry_change(self.layer_id, self.new_bounds)

    def undo(self):
        # 1. Restore the old bounds and patch
        self.session._apply_geometry_change(self.layer_id, self.old_bounds)
        
        # 2. Restore the old mask explicitly (Instant Undo)
        # We skip re-segmentation because we saved the previous good result
        layer = self.session.layers[self.layer_id]
        layer.raw_mask = self.old_mask
        self.session.logger.info(f"Undo Geometry: Restored bounds and mask for {self.layer_id}")

    def __str__(self):
        return f"Geometry Change Layer {self.layer_id}: {self.old_bounds} -> {self.new_bounds}"
    

class AddLayerCommand(Command):
    def __init__(self, session, layer_id):
        self.session = session
        self.layer_id = layer_id
        # Capture the created layer object so we can restore it on Redo
        # without needing to regenerate masks or re-slice pixels.
        self.layer = session.layers[layer_id]

    def execute(self):
        # Redo: Put the layer object back into the session
        self.session.layers[self.layer_id] = self.layer
        self.session.logger.info(f"execute: Added layer {self.layer_id}")

    def undo(self):
        # Undo: Remove the layer from the session
        if self.layer_id in self.session.layers:
            del self.session.layers[self.layer_id]
            self.session.logger.info(f"Undo: Removed layer {self.layer_id}")

    def __str__(self):
        return f"Add Layer {self.layer_id}"
    



class DeleteLayerCommand(Command):
    """
        Delete layer  only removes the full size mask but retains other mask, 
        so that undo can bring things back for proxy image  (soft cleanup)

        Hard cleanup is done only when the layer is finally overflown out of 
        undo stack and no more undo is possible
    """
    def __init__(self, session, layer_id):
        self.session = session
        self.layer_id = layer_id
        self.layer = session.layers.get(layer_id)

    def execute(self):
        if self.layer_id in self.session.layers:
            # SOFT CLEANUP: 
            # We don't nullify proxy_patch because Undo needs it.
            # But we can clear the strategy_cache to free up the 50MP masks.
            if self.layer:
                self.layer.strategy_cache.clear() 
            
            del self.session.layers[self.layer_id]
            self.session.logger.info(f"Executed Delete: {self.layer_id}")

    def undo(self):
        if self.layer:
            # Because we cleared the cache in execute(), 
            # the first slider move after Undo will simply re-run the 
            # (fast) proxy AI detection. This is a safe trade-off.
            self.session.layers[self.layer_id] = self.layer
            self.session.logger.info(f"Undo Delete: Restored {self.layer_id}")
            

    def on_evicted_from_undo_stack(self):
        """
        Hard cleanup . Commandprocessor will run this only when we are pushed past the stack bottom
        The 'Point of No Return' - Wipe the memory. 
        Till now soft clenup lkept the smaller masks in memory (even if layer was deleted )
        """
        if self.layer:
            # This layer is no longer undoable. Kill everything.
            self.layer.release_resources() 
            self.layer.proxy_patch = None # Hard wipe
            self.layer = None # Break reference for GC
