bl_info = {
    "name": "Breakdowner",
    "description": "Breakdown in object mode",
    "author": "Samuel Bernou",
    "version": (1, 0, 0),
    "blender": (2, 93, 0),
    "location": "View3D",
    "doc_url": "https://github.com/Pullusb/breakdowner",
    "tracker_url": "https://github.com/Pullusb/breakdowner/issues",
    "category": "Object" }

import bpy
import re
from mathutils import Vector, Matrix
from math import radians, degrees

# extracted from GP toolbox Breakdowner object mode V1
# exemple for future improve: https://justinsbarrett.com/tweenmachine/

def get_surrounding_points(fc, frame):
    '''Take an Fcurve and a frame and return previous and next frames'''
    if not frame: frame = bpy.context.scene.frame_current
    p_pt = n_pt = None
    mins = []
    maxs = []
    for pt in fc.keyframe_points:
        if pt.co[0] < frame:
            p_pt = pt
        if pt.co[0] > frame:
            n_pt = pt
            break
    
    return p_pt, n_pt

## unused direct breackdown func
def breakdown_keys(percentage=50, channels=('location', 'rotation_euler', 'scale'), axe=(0,1,2)):
    cf = bpy.context.scene.frame_current# use operator context (may be unsynced timeline)
    axes_name = ('x', 'y', 'z')
    obj = bpy.context.object# better use self.context
    if not obj:
        print('no active object')
        return
    
    anim_data = obj.animation_data
    if not anim_data:
        print(f'no animation data on obj: {obj.name}')
        return
    
    action = anim_data.action
    if not action:
        print(f'no action on animation data of obj: {obj.name}')
        return
    
    skipping = []

    for fc in action.fcurves:
        # if fc.data_path.split('"')[1] in bone_names_filter:# bones
        # if fc.data_path.split('.')[-1] in channels and fc.array_index in axe:# bones
        if fc.data_path in channels and fc.array_index in axe:# .split('.')[-1]
            fc_name = f'{fc.data_path}.{axes_name[fc.array_index]}'
            print(fc_name)
            pkf, nkf = get_surrounding_points(fc, frame=cf)
            # check previous, next keyframe (if one or both is missing, skip)
            if pkf is None or nkf is None:
                skipping.append(fc_name)
                continue

            prv, nxt = pkf.co[1], nkf.co[1]
            if prv == nxt:
                nval = prv
            else:
                nval = ((percentage * (nxt - prv)) / 100) + prv#intermediate val
                print('value:', nval)

            fc.keyframe_points.add(1)
            fc.keyframe_points[-1].co[0] = cf
            fc.keyframe_points[-1].co[1] = nval
            fc.keyframe_points[-1].type = pkf.type# make same type ?
            fc.keyframe_points[-1].interpolation = pkf.interpolation
            fc.update()
            # obj.keyframe_insert(fc.data_path, index=fc.array_index, )
            
### breakdown_keys(channels=('location', 'rotation_euler', 'scale'))

class OBJECT_OT_breakdown_anim(bpy.types.Operator):
    """Breakdown percentage between two keyframes like bone pose mode"""
    bl_idname = "object.breakdown_anim"
    bl_label = "breakdown object keyframe"
    bl_description = "Percentage value between previous and next keyframes"
    bl_options = {"REGISTER", "UNDO"}

    pressed_ctrl = False
    pressed_shift = False
    str_val = ''
    step = 5

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'and context.object

    def percentage(self):
        return (self.xmouse - self.xmin) / self.width * 100

    def assign_transforms(self, percentage):
        for obj, path_dic in self.obdic.items():
            for data_path, index_dic in path_dic.items():
                for index, vals in index_dic.items():# prv, nxt = vals
                    # exec(f'bpy.data.objects["{obj.name}"].{data_path}[{index}] = {((self.percentage() * (vals[1] - vals[0])) / 100) + vals[0]}')
                    getattr(obj, data_path)[index] = ((percentage * (vals[1] - vals[0])) / 100) + vals[0]

    def modal(self, context, event):
        context.area.tag_redraw()
        refresh = False

        ## Handle modifier keys state
        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}: self.pressed_shift = event.value == 'PRESS'
        if event.type in {'LEFT_CTRL', 'RIGHT_CTRL'}: self.pressed_ctrl = event.value == 'PRESS'

        ### KEYBOARD SINGLE PRESS
        if event.value == 'PRESS':
            refresh=True
            if event.type in {'NUMPAD_MINUS'}:#, 'LEFT_BRACKET', 'WHEELDOWNMOUSE'
                if self.str_val.startswith('-'):
                    self.str_val = self.str_val.strip('-')
                else:
                    self.str_val = '-' + self.str_val#.strip('-')
            
            ## number
            if event.type in {'ZERO', 'NUMPAD_0'}: self.str_val += '0'
            if event.type in {'ONE', 'NUMPAD_1'}: self.str_val += '1'
            if event.type in {'TWO', 'NUMPAD_2'}: self.str_val += '2'
            if event.type in {'THREE', 'NUMPAD_3'}: self.str_val += '3'
            if event.type in {'FOUR', 'NUMPAD_4'}: self.str_val += '4'
            if event.type in {'FIVE', 'NUMPAD_5'}: self.str_val += '5'
            if event.type in {'SIX', 'NUMPAD_6'}: self.str_val += '6'
            if event.type in {'SEVEN', 'NUMPAD_7'}: self.str_val += '7'
            if event.type in {'EIGHT', 'NUMPAD_8'}: self.str_val += '8'
            if event.type in {'NINE', 'NUMPAD_9'}: self.str_val += '9'

            if event.type in {'NUMPAD_PERIOD', 'COMMA'}:
                if not '.' in self.str_val: self.str_val += '.'
            
            # remove end chars
            if event.type in {'DEL', 'BACK_SPACE'}: self.str_val = self.str_val[:-1]

            # TODO lock transforms
            # if event.type in {'G'}:pass# grab translate only
            # if event.type in {'R'}:pass# rotation only
            # if event.type in {'S'}:pass# scale only

        ## TODO need to check if self.str_val is valid and if not : display warning and return running modal

        if re.search(r'\d', self.str_val):
            use_num = True
            percentage = float(self.str_val)
            
            display_percentage = f'{percentage:.1f}' if '.' in self.str_val else f'{percentage:.0f}'
            display_text = f'Breakdown: [{display_percentage}]% | manual type, erase for mouse control'

        else: # use mouse
            use_num = False
            percentage = self.percentage()
            if self.pressed_ctrl:# round
                percentage = int(percentage)
            if self.pressed_shift:# by step of 5
                modulo = percentage % self.step
                if modulo < self.step/2.0:                    
                    percentage = int( percentage - modulo )
                else:
                    percentage = int( percentage + (self.step - modulo) )
            
            display_percentage = f'{percentage:.1f}' if isinstance(percentage, float) else str(percentage)
            display_text = f'Breakdown: {display_percentage}% | MODES ctrl: round - shift: 5 steps'

        context.area.header_text_set(display_text)
        
        ## Get mouse move
        if event.type in {'MOUSEMOVE'}:# , 'INBETWEEN_MOUSEMOVE'
            if not use_num: # avoid compute on mouse move when manual type on
                refresh = True
            
            ## percentage of xmouse in screen
            self.xmouse = event.mouse_region_x

        if refresh:
            self.assign_transforms(percentage)


        # Valid
        if event.type in {'RET', 'SPACE', 'LEFTMOUSE'}:
                ## 'INSERTKEY_AVAILABLE' ?  ? filter
            context.area.header_text_set(None)
            context.window.cursor_set("DEFAULT")
            
            if context.scene.tool_settings.use_keyframe_insert_auto:# auto key OK
                if context.scene.tool_settings.use_keyframe_insert_keyingset and context.scene.keying_sets_all.active:
                    bpy.ops.anim.keyframe_insert('INVOKE_DEFAULT')#type='DEFAULT'
                else:
                    bpy.ops.anim.keyframe_insert('INVOKE_DEFAULT', type='Available')
                    # "DEFAULT" not found in ('Available', 'Location', 'Rotation', 'Scaling', 'BUILTIN_KSI_LocRot', 'LocRotScale', 'BUILTIN_KSI_LocScale', 'BUILTIN_KSI_RotScale', 'BUILTIN_KSI_DeltaLocation', 'BUILTIN_KSI_DeltaRotation', 'BUILTIN_KSI_DeltaScale', 'BUILTIN_KSI_VisualLoc', 'BUILTIN_KSI_VisualRot', 'BUILTIN_KSI_VisualScaling', 'BUILTIN_KSI_VisualLocRot', 'BUILTIN_KSI_VisualLocRotScale', 'BUILTIN_KSI_VisualLocScale', 'BUILTIN_KSI_VisualRotScale')
            return {'FINISHED'}
        
        # Abort
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            ## Remove draw handler (if there was any)
            # bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

            context.scene.frame_set(self.cf)# reset object pos (update scene to re-evaluate anim)
            context.area.header_text_set(None)#reset header
            context.window.cursor_set("DEFAULT")
            # print('Breakdown Cancelled')#Dbg
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        ## cursors
        ## 'DEFAULT', 'NONE', 'WAIT', 'CROSSHAIR', 'MOVE_X', 'MOVE_Y', 'KNIFE', 'TEXT', 'PAINT_BRUSH', 'PAINT_CROSS', 'DOT', 'ERASER', 'HAND', 'SCROLL_X', 'SCROLL_Y', 'SCROLL_XY', 'EYEDROPPER'
        ## start checks 
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'View3D not found, cannot run operator')
            return {'CANCELLED'}

        obj = bpy.context.object# better use self.context
        if not obj:
            self.report({'WARNING'}, 'No active object')
            return {'CANCELLED'}
        
        anim_data = obj.animation_data
        if not anim_data:
            self.report({'WARNING'}, f'No animation data on obj: {obj.name}')
            return {'CANCELLED'}
        
        action = anim_data.action
        if not action:
            self.report({'WARNING'}, f'No action on animation data of obj: {obj.name}')
            return {'CANCELLED'}

        ## initiate variable to use
        self.width = context.area.width# include sidebar...
        ## with exclude sidebar >>> C.screen.areas[3].regions[5].width

        self.xmin = context.area.x

        self.xmouse = event.mouse_region_x
        self.pressed_alt = event.alt
        self.pressed_ctrl = event.ctrl
        self.pressed_shift = event.shift
        
        self.cf = context.scene.frame_current
        self.channels = ('location', 'rotation_euler', 'rotation_quaternion', 'scale')

        skipping = []
        found = 0
        same = 0

        self.obdic = {}

        ## TODO for ob in context.selected objects, need to reduce list with upper filters...

        for fc in action.fcurves:
            # if fc.data_path.split('"')[1] in bone_names_filter:# bones
            # if fc.data_path.split('.')[-1] in channels and fc.array_index in axe:# bones
            if fc.data_path in self.channels:# .split('.')[-1]# and fc.array_index in axe
                fc_name = f'{fc.data_path}.{fc.array_index}'
                pkf, nkf = get_surrounding_points(fc, frame = self.cf)
                
                if pkf is None or nkf is None:
                    # check previous, next keyframe (if one or both is missing, skip)
                    skipping.append(fc_name)
                    continue
                
                found +=1
                prv, nxt = pkf.co[1], nkf.co[1]
                
                if not obj in self.obdic:
                    self.obdic[obj] = {} 

                if not fc.data_path in self.obdic[obj]:
                    self.obdic[obj][fc.data_path] = {}

                self.obdic[obj][fc.data_path][fc.array_index] = [prv, nxt]

                if prv == nxt:
                    same += 1
                else:
                    # exec(f'bpy.data.objects["{obj.name}"].{fc.data_path}[{fc.array_index}] = {((self.percentage() * (nxt - prv)) / 100) + prv}')
                    getattr(obj, fc.data_path)[fc.array_index] = ((self.percentage() * (nxt - prv)) / 100) + prv
        
        '''# debug print value dic
        import pprint
        print('\nDIC print: ')
        pprint.pprint(self.obdic)
        '''

        if not found:
            self.report({'ERROR'}, "No key pairs to breakdown found ! need to be between a key pair")# 
            return {'CANCELLED'}

        if found == same:
            self.report({'ERROR'}, "All Key pairs found have same values")# 
            return {'CANCELLED'}
        ## Starts the modal
        context.window.cursor_set("SCROLL_X")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


### --- KEYMAP ---

breakdowner_addon_keymaps = []
def register_keymaps():
    addon = bpy.context.window_manager.keyconfigs.addon
    try:
        km = bpy.context.window_manager.keyconfigs.addon.keymaps["3D View"]
    except Exception as e:
        km = addon.keymaps.new(name = "3D View", space_type = "VIEW_3D")
        pass

    ops_id = 'object.breakdown_anim'
    if ops_id not in km.keymap_items: # avoid double register
        km = addon.keymaps.new(name='3D View', space_type='VIEW_3D')#EMPTY
        kmi = km.keymap_items.new(ops_id, type="E", value="PRESS", shift=True)
        breakdowner_addon_keymaps.append((km, kmi))

def unregister_keymaps():
    for km, kmi in breakdowner_addon_keymaps:
        km.keymap_items.remove(kmi)

    breakdowner_addon_keymaps.clear()

### --- REGISTER ---

def register():
    if bpy.app.background:
        return

    bpy.utils.register_class(OBJECT_OT_breakdown_anim)
    register_keymaps()

def unregister():
    if bpy.app.background:
        return

    unregister_keymaps()
    bpy.utils.unregister_class(OBJECT_OT_breakdown_anim)


if __name__ == "__main__":
    register()
