# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# ############################################################################################
# Controller for TweakPanel (Right Sidebar) with sliders 
# ############################################################################################

from ...backend.Interfaces import APP_NAME, StrategyScope

class PropertyManager:
    """
    Handles the bridge between Backend Data (Layers/Strategies) 
    and the Frontend UI (TweaksPanel).
    Responsibilities:
    1. Determine which controls to show for a selected layer. 
    2. Route slider changes to the correct backend function. 
    3. Decouple MainWindow from specific strategy names. 
    """
    def __init__(self, session, prop_panel, update_callback):
        """
        Args:
            session: The ImageSession backend. 
            prop_panel: The TweaksPanel widget. 
            update_callback: Function to call when display needs refresh (usually MainWindow.on_property_updated). 
        """
        self.session = session
        self.panel = prop_panel
        self.update_callback = update_callback
        
        # State tracking
        self.current_layer_id = None
        self.param_map = {} 

    def set_session(self, session):
        self.session = session

    

    def refresh_for_layer(self, layer_id):
        """
        Defines what strategies to include for this layer, based on the Layer Type. 
        then calls TweaksPanel's rebuild_for_layer which  handles sync/build logic internally.  
        Enforces 'isGlobal' contract. 

        final_groups dict decides exactly how the TweakPanle will look. wile strategies bring in their 
         own meta , we add two extra panels to control Mask Edge and LAyer Strength 
         We do this my manually filling  in the meta for these two panels  
        """
        self.current_layer_id = layer_id
        
        if not self.session or not layer_id:
            self.panel.setEnabled(False)
            return

        # 1. Define allowed strategies 
        if layer_id == self.session.BACKGROUND_ID:
            allowed_strategies = ["auto_wb", "whitebalance", "blur", "color", "tonalbalance"] 
        else:
            # allowed_strategies = ["auto_wb", "whitebalance", "blur", "parabright", 
            #                       "selective","color",  "facelight","facelight3D", 
            #                       "smart_skin","eyesparks","tonalbalance"]
            allowed_strategies = [ "blur", "color", "facelight3D", 
                                  "smart_skin","eyesparks","tonalbalance"]


        strategy_metas = {} # for strategies' metadata
        self.param_map = {} # Reset map
    
        # 2. Harvest Metadata from Backend Strategies
        for s_key, strategy in self.session.strategies.items():
            if s_key not in allowed_strategies:
                continue
            
            # --- GLOBAL CONTRACT CHECK ---
            # If a strategy is global, it ONLY appears on the Background Layer. 
            # We strictly hide it for standard layers. 
            if getattr(strategy, 'isGlobal', False) and layer_id != self.session.BACKGROUND_ID:
                continue

            meta = strategy.get_metadata()
            scope = getattr(strategy, 'scope', StrategyScope.LAYER)
            
           
            # We use namespace keys (e.g. 'facelight3D:light_strength') 
            # as different strategies may use the same parameter name.
            namespaced_meta = {}
            for p_name, p_config in meta.items():
                ui_key = f"{s_key}:{p_name}"
                namespaced_meta[ui_key] = p_config
                # Map the UI key to the strategy key for routing in _on_ui_change
                self.param_map[ui_key] = s_key

            # Store as tuple: (Scope, Metadata)
            strategy_metas[s_key.upper()] = (scope, namespaced_meta)

        layer = self.session.layers.get(layer_id)
        if not layer: return

        # 3. Assemble Groups
        if layer_id == self.session.BACKGROUND_ID:
            final_groups = strategy_metas
        else:
            # Manual groups (Mask/Layer) don't need namespaces as they are unique to the layer
            final_groups = {
                "Mask Edge": (StrategyScope.LAYER, {
                    "mask_threshold": {"type": "slider", "range": (0.1, 0.95), "label": "Threshold", "default": 0.5},
                    "mask_expand": {"type": "slider", "range": (-50, 50), "label": "Expand"},
                    "mask_feather": {"type": "slider", "range": (0, 100), "label": "Feather (%)", "default": 30}
                }),
                **strategy_metas,
                "Layer": (StrategyScope.LAYER, {
                    "opacity": {"type": "slider", "range": (0.0, 1.0), "label": "Opacity", "default": 1.0},
                    "effect_strength": {"type": "slider", "range": (0.0, 1.0), "label": "Strength", "default": 1.0}
                }),
            }

        # 4. Routing to Persistent Panel
        self.panel.rebuild_for_layer(layer_id, final_groups, layer.state, self._on_ui_change)
        self.panel.setEnabled(True)

    def _on_ui_change(self, ui_key, val, is_final, old_val):
        """
        Unified callback for ALL property sliders.
        Routes the change to the correct backend function. 
        """
        if not self.current_layer_id: return
        lid = self.current_layer_id

        # Route 1: Standard Layer/Mask Properties (No colon in key)
        if lid != self.session.BACKGROUND_ID and \
            ui_key in ["mask_threshold", "mask_expand", "mask_feather", "mask_contrast", "opacity", "effect_strength"]:
            self.session.update_layer_property(lid, ui_key, val, is_final, old_val)

        # Route 2: Strategy Parameters (Namespaced: 'strat:param')
        elif ui_key in self.param_map:
            strategy_key = self.param_map[ui_key]
            # Strip namespace to send the clean param name to the backend
            actual_p_name = ui_key.split(":")[-1] if ":" in ui_key else ui_key
            self.session.update_layer_param(lid, strategy_key, actual_p_name, val, is_final, old_val)

        # Notify MainWindow to repaint
        if self.update_callback:
            self.update_callback(lid, ui_key)
            