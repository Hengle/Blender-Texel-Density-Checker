bl_info = {
	"name": "Texel Density Checker",
	"description": "Tools for for checking Texel Density and wasting of uv space",
	"author": "Ivan 'mrven' Vostrikov, Toomas Laik",
	"version": (1, 1, 0),
	"blender": (2, 80, 0),
	"location": "3D View > Toolbox",
	"category": "Object",
}

import bpy
import bmesh
import math
import tempfile
import sqlite3
import time
import os

from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        )
		
from bpy.props import (
		StringProperty,
		EnumProperty,
        BoolProperty,
        PointerProperty,
        )

#-------------------------------------------------------
class Texel_Density_Check(Operator):
	"""Check Density"""
	bl_idname = "object.texel_density_check"
	bl_label = "Check Texel Density"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		td = context.scene.td
		
		message = "TD is calculated"
		#save current mode and active object
		actObj = bpy.context.active_object
		current_selected_obj = bpy.context.selected_objects
		try:
			actObjType = actObj.type
			start_mode = bpy.context.object.mode
		except:
			actObjType = 'None'
			start_mode = 'OBJECT'
		current_mode = start_mode
		
		#proceed if active object is mesh
		if (actObjType == 'MESH' and len(actObj.data.uv_layers) > 0):
			if (bpy.context.object.mode == 'EDIT') and (td.selected_faces == True):
				bpy.ops.object.mode_set(mode='OBJECT')
				bpy.ops.object.select_all(action='DESELECT')
				actObj.select_set(True)
				bpy.ops.object.duplicate()
				bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
				#set default values
				Area=0
				gmArea = 0
				textureSizeCurX = 1024
				textureSizeCurY = 1024
				
				#Get texture size from panel
				if td.texture_size == '0':
					textureSizeCurX = 512
					textureSizeCurY = 512
				if td.texture_size == '1':
					textureSizeCurX = 1024
					textureSizeCurY = 1024
				if td.texture_size == '2':
					textureSizeCurX = 2048
					textureSizeCurY = 2048
				if td.texture_size == '3':
					textureSizeCurX = 4096
					textureSizeCurY = 4096
				if td.texture_size == '4':
					try:
						textureSizeCurX = int(td.custom_width)
					except:
						textureSizeCurX = 1024
						message = "Width value is wrong. Height will be set to 1024"
					try:
						textureSizeCurY = int(td.custom_height)
					except:
						textureSizeCurY = 1024
						message = "Height value is wrong. Height will be set to 1024"
				#get bmesh from active object
				bpy.ops.object.mode_set(mode='OBJECT')
				face_count = len(bpy.context.active_object.data.polygons)
				selected_faces = []
				for faceid in range (0, face_count):
					if bpy.context.active_object.data.polygons[faceid].select == True:
						selected_faces.append(faceid)
						
				bpy.ops.object.mode_set(mode='EDIT')
				bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
				bm.faces.ensure_lookup_table()
				for x in selected_faces:
					#set default values for multiplication of vectors (uv and physical area of object)
					multiVector = 0
					gmmultiVector = 0
					#UV Area calculating
					#get uv-coordinates of vertexes of current triangle
					loopA = bm.faces[x].loops[0][bm.loops.layers.uv.active].uv
					loopB = bm.faces[x].loops[1][bm.loops.layers.uv.active].uv
					loopC = bm.faces[x].loops[2][bm.loops.layers.uv.active].uv
					#get multiplication of vectors of current triangle
					multiVector = Vector2dMultiple(loopA, loopB, loopC)
					#Increment area of current tri to total uv area
					Area+=0.5*multiVector

					#Phisical Area calculating
					#get world coordinates of vertexes of current triangle
					gmloopA = bm.faces[x].loops[0].vert.co
					gmloopB = bm.faces[x].loops[1].vert.co
					gmloopC = bm.faces[x].loops[2].vert.co
					#get multiplication of vectors of current triangle
					gmmultiVector = Vector3dMultiple(gmloopA, gmloopB, gmloopC)
					#Increment area of current tri to total phisical area
					gmArea += 0.5*gmmultiVector
					
				bpy.ops.object.mode_set(mode='OBJECT')
				
				if len(selected_faces) > 0:
					#UV Area in percents
					UVspace = Area * 100
					
					aspectRatio = textureSizeCurX / textureSizeCurY;
					if aspectRatio < 1:
						aspectRatio = 1 / aspectRatio
					largestSide = textureSizeCurX if textureSizeCurX > textureSizeCurY else textureSizeCurY;
					#TexelDensity calculating from selected in panel texture size
					TexelDensity = ((largestSide / math.sqrt(aspectRatio)) * math.sqrt(Area))/(math.sqrt(gmArea)*100) / bpy.context.scene.unit_settings.scale_length

					#show calculated values on panel
					td.uv_space = '%.3f' % round(UVspace, 3) + ' %'
					if td.units == '0':
						td.density = '%.3f' % round(TexelDensity, 3)
					if td.units == '1':
						td.density = '%.3f' % round(TexelDensity*100, 3)
					if td.units == '2':
						td.density = '%.3f' % round(TexelDensity*2.54, 3)
					if td.units == '3':
						td.density = '%.3f' % round(TexelDensity*30.48, 3)
				else:
					self.report({'INFO'}, 'No faces selected')
				
				#delete duplicated object
				bpy.ops.object.delete()
				#select saved object
				for x in current_selected_obj:
					x.select_set(True)
				actObj.select_set(True)
				bpy.context.view_layer.objects.active = actObj
				bpy.ops.object.mode_set(mode='EDIT')
			#--------------------------------------------------
			#Calculating for all mesh
			else:
				#if start mode = edit, change to object mode
				if current_mode == 'EDIT':
					bpy.ops.object.mode_set(mode='OBJECT')
					current_mode = 'OBJECT'
				#Duplicate active object and triangulate mesh
				if current_mode == 'OBJECT':
					bpy.ops.object.select_all(action='DESELECT')
					actObj.select_set(True)
					bpy.ops.object.duplicate()
					bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
					bpy.ops.object.mode_set(mode='EDIT')
					bpy.ops.mesh.reveal()
					bpy.ops.mesh.select_all(action='DESELECT')
					bpy.ops.mesh.select_all(action='SELECT')
					bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

				#set default values
				Area=0
				gmArea = 0
				textureSizeCurX = 1024
				textureSizeCurY = 1024
				
				#Get texture size from panel
				if td.texture_size == '0':
					textureSizeCurX = 512
					textureSizeCurY = 512
				if td.texture_size == '1':
					textureSizeCurX = 1024
					textureSizeCurY = 1024
				if td.texture_size == '2':
					textureSizeCurX = 2048
					textureSizeCurY = 2048
				if td.texture_size == '3':
					textureSizeCurX = 4096
					textureSizeCurY = 4096
				if td.texture_size == '4':
					try:
						textureSizeCurX = int(td.custom_width)
					except:
						textureSizeCurX = 1024
						message = "Width value is wrong. Height will be set to 1024"
					try:
						textureSizeCurY = int(td.custom_height)
					except:
						textureSizeCurY = 1024
						message = "Height value is wrong. Height will be set to 1024"
				
				#get bmesh from active object
				bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
				bm.faces.ensure_lookup_table()

				#get faces and round this
				face_count = len(bm.faces)
				for faceid in range (0, face_count):
					#set default values for multiplication of vectors (uv and physical area of object)
					multiVector = 0
					gmmultiVector = 0
					#UV Area calculating
					#get uv-coordinates of vertexes of current triangle
					loopA = bm.faces[faceid].loops[0][bm.loops.layers.uv.active].uv
					loopB = bm.faces[faceid].loops[1][bm.loops.layers.uv.active].uv
					loopC = bm.faces[faceid].loops[2][bm.loops.layers.uv.active].uv
					#get multiplication of vectors of current triangle
					multiVector = Vector2dMultiple(loopA, loopB, loopC)
					#Increment area of current tri to total uv area
					Area+=0.5*multiVector

					#Phisical Area calculating
					#get world coordinates of vertexes of current triangle
					gmloopA = bm.faces[faceid].loops[0].vert.co
					gmloopB = bm.faces[faceid].loops[1].vert.co
					gmloopC = bm.faces[faceid].loops[2].vert.co
					#get multiplication of vectors of current triangle
					gmmultiVector = Vector3dMultiple(gmloopA, gmloopB, gmloopC)
					#Increment area of current tri to total physical area
					gmArea += 0.5*gmmultiVector
					
				#UV Area in percents
				UVspace = Area * 100
				
				aspectRatio = textureSizeCurX / textureSizeCurY;
				if aspectRatio < 1:
					aspectRatio = 1 / aspectRatio
				largestSide = textureSizeCurX if textureSizeCurX > textureSizeCurY else textureSizeCurY;
				#TexelDensity calculating from selected in panel texture size
				TexelDensity = ((largestSide / math.sqrt(aspectRatio)) * math.sqrt(Area))/(math.sqrt(gmArea)*100) / bpy.context.scene.unit_settings.scale_length
				
				#show calculated values on panel
				td.uv_space = '%.3f' % round(UVspace, 3) + ' %'
				if td.units == '0':
					td.density = '%.3f' % round(TexelDensity, 3)
				if td.units == '1':
					td.density = '%.3f' % round(TexelDensity*100, 3)
				if td.units == '2':
					td.density = '%.3f' % round(TexelDensity*2.54, 3)
				if td.units == '3':
					td.density = '%.3f' % round(TexelDensity*30.48, 3)
				#set object mode and delete duplicated object
				bpy.ops.object.mode_set(mode='OBJECT')
				bpy.ops.object.delete()
				#select saved object and return into initial mode
				for x in current_selected_obj:
					x.select_set(True)
				actObj.select_set(True)
				bpy.context.view_layer.objects.active = actObj
				
				bpy.ops.object.mode_set(mode=start_mode)
			
			self.report({'INFO'}, message)
			
		else:
			
			self.report({'ERROR'}, 'Active object isn''t a mesh or doesn\'t have UV')
		
		return {'FINISHED'}

#-------------------------------------------------------
class Texel_Density_Set(Operator):
	"""Set Density"""
	bl_idname = "object.texel_density_set"
	bl_label = "Set Texel Density"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		td = context.scene.td
		
		message = "TD is changed"
		enSetTD = True
		actObj = bpy.context.active_object
		current_selected_obj = bpy.context.selected_objects
		
		destiny_set_filtered = td.density_set.replace(',', '.')
		
		try:
			bpy.ops.object.texel_density_check()
		except:
			message = "Try Calculate TD before"
			enSetTD = False
		densityCurrentValue = float(td.density)
		try:
			densityNewValue = float(destiny_set_filtered)
		except:
			densityNewValue = densityCurrentValue
			message = "Density value is wrong"
		if enSetTD:
			if (densityNewValue != 0):
				if (bpy.context.object.mode == 'EDIT') and (td.selected_faces == True):
					scaleFac = densityNewValue/densityCurrentValue
					#check opened image editor window
					IE_area = 0
					flag_exist_area = False
					for area in range(len(bpy.context.screen.areas)):
						if bpy.context.screen.areas[area].type == 'IMAGE_EDITOR':
							IE_area = area
							flag_exist_area = True
							bpy.context.screen.areas[area].type = 'CONSOLE'
					
					bpy.context.area.type = 'IMAGE_EDITOR'
					
					if bpy.context.area.spaces[0].image != None:
						if bpy.context.area.spaces[0].image.name == 'Render Result':
							bpy.context.area.spaces[0].image = None
					
					if bpy.context.space_data.mode != 'UV':
						bpy.context.space_data.mode = 'UV'
					
					if bpy.context.scene.tool_settings.use_uv_select_sync == False:
						bpy.ops.uv.select_all(action = 'SELECT')
					
					bpy.ops.transform.resize(value=(scaleFac, scaleFac, 1))
					if td.set_method == '0':
						bpy.ops.uv.average_islands_scale()
					bpy.context.area.type = 'VIEW_3D'
					
					bpy.ops.object.texel_density_check()
					
					if flag_exist_area == True:
						bpy.context.screen.areas[IE_area].type = 'IMAGE_EDITOR'

				else:
					scaleFac = densityNewValue/densityCurrentValue
					#check opened image editor window
					IE_area = 0
					flag_exist_area = False
					for area in range(len(bpy.context.screen.areas)):
						if bpy.context.screen.areas[area].type == 'IMAGE_EDITOR':
							IE_area = area
							flag_exist_area = True
							bpy.context.screen.areas[area].type = 'CONSOLE'
							
					start_mode = bpy.context.object.mode
					
					if start_mode == 'OBJECT':
						bpy.ops.object.mode_set(mode='EDIT')
					
					bpy.ops.mesh.reveal()
					bpy.ops.mesh.select_all(action='DESELECT')
					bpy.ops.mesh.select_all(action='SELECT')
					
					bpy.context.area.type = 'IMAGE_EDITOR'
					
					if bpy.context.area.spaces[0].image != None:
						if bpy.context.area.spaces[0].image.name == 'Render Result':
							bpy.context.area.spaces[0].image = None
							
					if bpy.context.space_data.mode != 'UV':
						bpy.context.space_data.mode = 'UV'
					
					bpy.ops.uv.select_all(action = 'SELECT')
					bpy.ops.transform.resize(value=(scaleFac, scaleFac, 1))
					if td.set_method == '0':
						bpy.ops.uv.average_islands_scale()
					bpy.context.area.type = 'VIEW_3D'
					bpy.ops.object.mode_set(mode=start_mode)
					
					bpy.ops.object.texel_density_check()
					
					if flag_exist_area == True:
						bpy.context.screen.areas[IE_area].type = 'IMAGE_EDITOR'
			else:
				message = "Density must be greater than 0"
		self.report({'INFO'}, message)
		
		for x in current_selected_obj:
			x.select_set(True)
		actObj.select_set(True)
		bpy.context.view_layer.objects.active = actObj		
		return {'FINISHED'}
		
#-------------------------------------------------------
class Texel_Density_Copy(Operator):
	"""Copy Density"""
	bl_idname = "object.texel_density_copy"
	bl_label = "Copy Texel Density"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		td = context.scene.td
		
		message = "TD is copied"
		enCopyTD = True
		current_selected_obj = bpy.context.selected_objects
		actObj = bpy.context.active_object
		try:
			bpy.ops.object.texel_density_check()
		except:
			message = "Try Calculate TD before"
			enCopyTD = False
		densitySourceObject = float(td.density)
		
		if enCopyTD:
			for x in current_selected_obj:
				bpy.ops.object.select_all(action='DESELECT')
				if (x.type == 'MESH' and len(x.data.uv_layers) > 0):
					x.select_set(True)
					bpy.context.view_layer.objects.active = x
					bpy.ops.object.texel_density_check()
					densityCurrentValue = float(td.density)
					scaleFac = densitySourceObject/densityCurrentValue
				
					IE_area = 0
					flag_exist_area = False
					for area in range(len(bpy.context.screen.areas)):
						if bpy.context.screen.areas[area].type == 'IMAGE_EDITOR':
							IE_area = area
							flag_exist_area = True
							bpy.context.screen.areas[area].type = 'CONSOLE'
					
					bpy.ops.object.mode_set(mode='EDIT')
					
					bpy.ops.mesh.reveal()
					bpy.ops.mesh.select_all(action='DESELECT')
					bpy.ops.mesh.select_all(action='SELECT')
					
					bpy.context.area.type = 'IMAGE_EDITOR'
					
					if bpy.context.area.spaces[0].image != None:
						if bpy.context.area.spaces[0].image.name == 'Render Result':
							bpy.context.area.spaces[0].image = None
							
					if bpy.context.space_data.mode != 'UV':
						bpy.context.space_data.mode = 'UV'
					
					bpy.ops.uv.select_all(action = 'SELECT')
					bpy.ops.transform.resize(value=(scaleFac, scaleFac, 1))
					bpy.ops.uv.average_islands_scale()
					bpy.context.area.type = 'VIEW_3D'
					bpy.ops.object.mode_set(mode='OBJECT')
				
					if flag_exist_area == True:
						bpy.context.screen.areas[IE_area].type = 'IMAGE_EDITOR'
		
		for x in current_selected_obj:
			x.select_set(True)
		
		actObj.select_set(True)
		bpy.context.view_layer.objects.active = actObj
		
		self.report({'INFO'}, message)
		
		return {'FINISHED'}

#-------------------------------------------------------
class Calculated_To_Set(Operator):
	"""Copy Calc to Set"""
	bl_idname = "object.calculate_to_set"
	bl_label = "Set Texel Density"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		td = context.scene.td
		
		td.density_set = td.density
		
		return {'FINISHED'}
		
#-------------------------------------------------------
class Preset_Set(Operator):
	"""Preset Set Density"""
	bl_idname = "object.preset_set"
	bl_label = "Set Texel Density"
	bl_options = {'REGISTER', 'UNDO'}
	TDValue: StringProperty()
	
	def execute(self, context):
		td = context.scene.td
		
		td.density_set = self.TDValue
		bpy.ops.object.texel_density_set()
				
		return {'FINISHED'}
		
#-------------------------------------------------------
class Select_Same_TD(Operator):
	"""Select Faces with same TD"""
	bl_idname = "object.select_same_texel"
	bl_label = "Select Faces with same TD"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		td = context.scene.td
		
		message = "Faces selected"
		actObj = bpy.context.active_object
		current_selected_obj = bpy.context.selected_objects
		
		#proceed if active object is mesh
		if (len(actObj.data.uv_layers) > 0):	
			#select mode faces
			bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
			#check number of faces
			selected_faces = 0
			face_count = len(bpy.context.active_object.data.polygons)
			
			bpy.ops.object.mode_set(mode='OBJECT')
			for x in range(0, face_count):
				if bpy.context.active_object.data.polygons[x].select == True:
					selected_faces += 1 
			bpy.ops.object.mode_set(mode='EDIT')
			
			if selected_faces > 1 or selected_faces < 1:
				message = "Select only one faces"
			else:
				selected_faces_mode_state = td.selected_faces
				td.selected_faces = True
				bpy.ops.object.texel_density_check()
				search_td_value = float(td.density)
				
				#proceed if active object is mesh
				bpy.ops.object.mode_set(mode='OBJECT')
				bpy.ops.object.select_all(action='DESELECT')
				actObj.select_set(True)
				bpy.ops.object.duplicate()
				bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

				#set default values
				Area=0
				gmArea = 0
				textureSizeCurX = 1024
				textureSizeCurY = 1024

				#Get texture size from panel
				if td.texture_size == '0':
					textureSizeCurX = 512
					textureSizeCurY = 512
				if td.texture_size == '1':
					textureSizeCurX = 1024
					textureSizeCurY = 1024
				if td.texture_size == '2':
					textureSizeCurX = 2048
					textureSizeCurY = 2048
				if td.texture_size == '3':
					textureSizeCurX = 4096
					textureSizeCurY = 4096
				if td.texture_size == '4':
					try:
						textureSizeCurX = int(td.custom_width)
					except:
						textureSizeCurX = 1024
						message = "Width value is wrong. Height will be set to 1024"
					try:
						textureSizeCurY = int(td.custom_height)
					except:
						textureSizeCurY = 1024
						message = "Height value is wrong. Height will be set to 1024"

				#Get polygon pool from original geometry
				#face_count = len(bpy.context.active_object.data.polygons)

				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='SELECT')
				bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
				bpy.ops.mesh.select_all(action='DESELECT')

				bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
				bm.faces.ensure_lookup_table()
				
				searched_faces=[]
				threshold_filtered = td.select_td_threshold.replace(',', '.')
				try:
					threshold_td_value = float(threshold_filtered)
				except:
					threshold_td_value = 0.1
					td.select_td_threshold = "0.1"
				
				for x in range(0, face_count):
					#set default values for multiplication of vectors (uv and physical area of object)
					multiVector = 0
					gmmultiVector = 0
					#UV Area calculating
					#get uv-coordinates of vertexes of current triangle
					loopA = bm.faces[x].loops[0][bm.loops.layers.uv.active].uv
					loopB = bm.faces[x].loops[1][bm.loops.layers.uv.active].uv
					loopC = bm.faces[x].loops[2][bm.loops.layers.uv.active].uv
					#get multiplication of vectors of current triangle
					multiVector = Vector2dMultiple(loopA, loopB, loopC)
					#Increment area of current tri to total uv area
					Area=0.5*multiVector

					#Phisical Area calculating
					#get world coordinates of vertexes of current triangle
					gmloopA = bm.faces[x].loops[0].vert.co
					gmloopB = bm.faces[x].loops[1].vert.co
					gmloopC = bm.faces[x].loops[2].vert.co
					#get multiplication of vectors of current triangle
					gmmultiVector = Vector3dMultiple(gmloopA, gmloopB, gmloopC)
					#Increment area of current tri to total physical area
					gmArea = 0.5*gmmultiVector
					
					aspectRatio = textureSizeCurX / textureSizeCurY;
					if aspectRatio < 1:
						aspectRatio = 1 / aspectRatio
					largestSide = textureSizeCurX if textureSizeCurX > textureSizeCurY else textureSizeCurY;
					#TexelDensity calculating from selected in panel texture size
					TexelDensity = ((largestSide / math.sqrt(aspectRatio)) * math.sqrt(Area))/(math.sqrt(gmArea)*100) / bpy.context.scene.unit_settings.scale_length

					#show calculated values on panel
					if td.units == '0':
						td.density = '%.3f' % round(TexelDensity, 3)
					if td.units == '1':
						td.density = '%.3f' % round(TexelDensity*100, 3)
					if td.units == '2':
						td.density = '%.3f' % round(TexelDensity*2.54, 3)
					if td.units == '3':
						td.density = '%.3f' % round(TexelDensity*30.48, 3)
					
					current_poly_td_value = float(td.density)
					
					if (current_poly_td_value > (search_td_value - threshold_td_value)) and (current_poly_td_value < (search_td_value + threshold_td_value)):
						searched_faces.append(x)
				
				bpy.ops.object.mode_set(mode='OBJECT')
				
				#delete duplicated object
				bpy.ops.object.delete()
				#select saved object
				for x in current_selected_obj:
					x.select_set(True)
		
				actObj.select_set(True)
				bpy.context.view_layer.objects.active = actObj
				
				bpy.ops.object.mode_set(mode='EDIT')
				bpy.ops.mesh.select_all(action='DESELECT')
				bpy.ops.object.mode_set(mode='OBJECT')
				
				for faceid in searched_faces:
					bpy.context.active_object.data.polygons[faceid].select = True
				bpy.ops.object.mode_set(mode='EDIT')
				
				message = "Faces Selected"
				td.selected_faces = selected_faces_mode_state
		else:
			message = "This object don't have uv"
			
		self.report({'INFO'}, message)

		return {'FINISHED'}
		
#-------------------------------------------------------
class Checker_Assign(Operator):
	"""Assign Checker Material"""
	bl_idname = "object.checker_assign"
	bl_label = "Assign Checker Material"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		td = context.scene.td

		checker_rexolution_x = 1024
		checker_rexolution_y = 1024
		
		#Get texture size from panel
		if td.texture_size == '0':
			checker_rexolution_x = 512
			checker_rexolution_y = 512
		if td.texture_size == '1':
			checker_rexolution_x = 1024
			checker_rexolution_y = 1024
		if td.texture_size == '2':
			checker_rexolution_x = 2048
			checker_rexolution_y = 2048
		if td.texture_size == '3':
			checker_rexolution_x = 4096
			checker_rexolution_y = 4096
		if td.texture_size == '4':
			try:
				checker_rexolution_x = int(td.custom_width)
			except:
				checker_rexolution_x = 1024
				message = "Width value is wrong. Height will be set to 1024"
				self.report({'INFO'}, message)
			try:
				checker_rexolution_y = int(td.custom_height)
			except:
				checker_rexolution_y = 1024
				message = "Height value is wrong. Height will be set to 1024"
				self.report({'INFO'}, message)

		#Check exist texture image
		flag_exist_texture = False
		for t in range(len(bpy.data.images)):
			if bpy.data.images[t].name == 'TD_Checker':
				flag_exist_texture = True
				
		# create or not texture
		if flag_exist_texture == False:
			bpy.ops.image.new(name='TD_Checker', width = checker_rexolution_x, height = checker_rexolution_y, generated_type='COLOR_GRID')
		else:
			bpy.data.images['TD_Checker'].generated_width = checker_rexolution_x
			bpy.data.images['TD_Checker'].generated_height = checker_rexolution_y

		#Check exist TD_Checker_mat
		flag_exist_material = False
		for m in range(len(bpy.data.materials)):
			if bpy.data.materials[m].name == 'TD_Checker':
				flag_exist_material = True
				
		# create or not material
		if flag_exist_material == False:
			td_checker_mat = bpy.data.materials.new('TD_Checker')
			td_checker_mat.use_nodes = True
			Nodes = td_checker_mat.node_tree.nodes
			Links = td_checker_mat.node_tree.links
			TexNode = Nodes.new('ShaderNodeTexImage')
			TexNode.location = (-500,0)
			TexNode.image = bpy.data.images['TD_Checker']
			Links.new(TexNode.outputs["Color"], Nodes['Principled BSDF'].inputs['Base Color'])
		
		bpy.ops.object.mode_set(mode = 'OBJECT')

		if td.checker_method == '1':
			if len(bpy.data.filepath) == 0:
				td.db_path = tempfile.gettempdir() + '//TD_Objects_' + str(time.time()) + '.db' 
				self.report({'INFO'}, "Used Temporary Storage!")
			else:
				filename = bpy.path.basename(bpy.data.filepath)
				filename = os.path.splitext(filename)[0]
				td.db_path = bpy.path.abspath('//TD_Objects_'+ filename +'.db')

			conn = sqlite3.connect(td.db_path)
			cursor = conn.cursor()
			
			try:
				cursor.execute("""CREATE TABLE objects(objectName text, materialID int, materialName text)""")
			except:
				print("Table objects exist")

			try:
				cursor.execute("""CREATE TABLE materials(objectName text, polygonID int, materialID int)""")
			except:
				print("Table materials exist")
			
			objects_in_db = cursor.execute("""SELECT DISTINCT objectName FROM objects""")
			
			db_obj_list = []
			for db_obj in objects_in_db:
				db_obj_list.append(db_obj[0])

			for obj in bpy.context.selected_objects:
				append_this_object = True
				for list_obj in db_obj_list:
					if list_obj == obj.name:
						append_this_object = False
				
				if obj.type == 'MESH' and append_this_object:
					if len(obj.data.materials) == 0:
						object_to_db = (obj.name, 0, 'Without mats')
						cursor.execute("""INSERT INTO objects VALUES (?, ?, ?)""", object_to_db)
					else:
						for mat in range(len(obj.data.materials)):
							if obj.data.materials[mat] == None:
								object_to_db = (obj.name, mat, 'None')
							else:
								object_to_db = (obj.name, mat, obj.data.materials[mat].name)
							cursor.execute("""INSERT INTO objects VALUES (?, ?, ?)""", object_to_db)

					for poly in range(len(obj.data.polygons)):
						polygon_to_db = (obj.name, poly, obj.data.polygons[poly].material_index)
						cursor.execute("""INSERT INTO materials VALUES (?, ?, ?)""", polygon_to_db)

			conn.commit()
			conn.close()

		if td.checker_method == '0':
			for o in bpy.context.selected_objects:
				if o.type == 'MESH' and len(o.data.materials) > 0:
					for q in reversed(range(len(o.data.materials))):
						bpy.context.object.active_material_index = q
						o.data.materials.pop(index = q, update_data=True)

			for o in bpy.context.selected_objects:
				if o.type == 'MESH':
					o.data.materials.append(bpy.data.materials['TD_Checker'])

		if td.checker_method == '1':
			start_active_obj = bpy.context.active_object
			start_selected_obj = bpy.context.selected_objects

			for o in start_selected_obj:
				bpy.ops.object.mode_set(mode = 'OBJECT')
				bpy.ops.object.select_all(action='DESELECT')
				if o.type == 'MESH':
					o.select_set(True)
					bpy.context.view_layer.objects.active = o
					o.data.materials.append(bpy.data.materials['TD_Checker'])
					mat_index = len(o.data.materials) - 1
					bpy.ops.object.mode_set(mode = 'EDIT')
					bpy.ops.mesh.reveal()
					bpy.ops.mesh.select_all(action='SELECT')
					bpy.context.object.active_material_index = mat_index
					bpy.ops.object.material_slot_assign()
					bpy.ops.object.mode_set(mode = 'OBJECT')

			for j in start_selected_obj:
				j.select_set(True)

			bpy.context.view_layer.objects.active = start_active_obj

			td.show_restore_mats_btn = True
				
		return {'FINISHED'}

#-------------------------------------------------------
class Checker_Restore(Operator):
	"""Restore Saved Materials"""
	bl_idname = "object.checker_restore"
	bl_label = "Restore Saved Materials"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		td = context.scene.td

		start_active_obj = bpy.context.active_object
		start_selected_obj = bpy.context.selected_objects

		bpy.ops.object.mode_set(mode = 'OBJECT')
		bpy.ops.object.select_all(action='DESELECT')

		conn = sqlite3.connect(td.db_path)
		cursor = conn.cursor()

		#Select Stored Object
		objects_in_db = cursor.execute("""SELECT DISTINCT objectName FROM objects""")
			
		db_obj_list = []
		for db_obj in objects_in_db:
			db_obj_list.append(db_obj[0])
			try:
				bpy.data.objects[db_obj[0]].select_set(True)
				bpy.context.view_layer.objects.active = bpy.data.objects[db_obj[0]]
			except:
				print("Object " + db_obj[0] + " no more exist")

		#Again Delete All materials
		for o in bpy.context.selected_objects:
			if o.type == 'MESH' and len(o.data.materials) > 0:
				for q in reversed(range(len(o.data.materials))):
					bpy.context.object.active_material_index = q
					o.data.materials.pop(index = q, update_data=True)

		#Assign Stored Materials to Material Slots. If material not exist - skip that, use empty material slot
		for obj in bpy.context.selected_objects:
			bpy.ops.object.select_all(action='DESELECT')
			obj.select_set(True)
			bpy.context.view_layer.objects.active = obj

			obj_mats_in_db = cursor.execute("""SELECT materialName, materialID FROM objects WHERE objectName = '"""+ obj.name +"""' ORDER BY materialID""")
			
			for obj_mat in obj_mats_in_db:
				if not obj_mat[0] == "Without mats":
					if not obj_mat[0] == "None":
						try:
							obj.data.materials.append(bpy.data.materials[obj_mat[0]])
						except:
							print("Can not append material " + obj_mat[0] + " to Slot " + str(obj_mat[1]) + " of Object" + obj.name)
							obj.data.materials.append(bpy.data.materials["TD_Checker"])
							obj.data.materials[obj_mat[1]] = None
					elif obj_mat[0] == "None":
						#Don't Ask me why
						obj.data.materials.append(bpy.data.materials["TD_Checker"])
						obj.data.materials[obj_mat[1]] = None

		#Assign Materials to Polygons. Maybe Get Object PolyCount and use that? It's helpful if object's geometry was changed.

		#Delete DB

		td.show_restore_mats_btn = False

		conn.commit()
		conn.close()
		
		bpy.ops.object.select_all(action='DESELECT')
		for x in start_selected_obj:
			x.select_set(True)
		bpy.context.view_layer.objects.active = start_active_obj
		print("Restore Saved Materials")
				
		return {'FINISHED'}

def Change_Texture_Size(self, context):
	td = context.scene.td

	#Check exist texture image
	flag_exist_texture = False
	for t in range(len(bpy.data.images)):
		if bpy.data.images[t].name == 'TD_Checker':
			flag_exist_texture = True
			
	if flag_exist_texture:
		checker_rexolution_x = 1024
		checker_rexolution_y = 1024
		
		#Get texture size from panel
		if td.texture_size == '0':
			checker_rexolution_x = 512
			checker_rexolution_y = 512
		if td.texture_size == '1':
			checker_rexolution_x = 1024
			checker_rexolution_y = 1024
		if td.texture_size == '2':
			checker_rexolution_x = 2048
			checker_rexolution_y = 2048
		if td.texture_size == '3':
			checker_rexolution_x = 4096
			checker_rexolution_y = 4096
		if td.texture_size == '4':
			try:
				checker_rexolution_x = int(td.custom_width)
			except:
				checker_rexolution_x = 1024
				message = "Width value is wrong. Height will be set to 1024"
				self.report({'INFO'}, message)
			try:
				checker_rexolution_y = int(td.custom_height)
			except:
				checker_rexolution_y = 1024
				message = "Height value is wrong. Height will be set to 1024"
				self.report({'INFO'}, message)

		bpy.data.images['TD_Checker'].generated_width = checker_rexolution_x
		bpy.data.images['TD_Checker'].generated_height = checker_rexolution_y

#-------------------------------------------------------
#FUNCTIONS
def Vector2dMultiple(A, B, C):
	return abs((B[0]- A[0])*(C[1]- A[1])-(B[1]- A[1])*(C[0]- A[0]))

def Vector3dMultiple(A, B, C):
	result = 0
	vectorX = 0
	vectorY = 0
	vectorZ = 0
	
	vectorX = (B[1]- A[1])*(C[2]- A[2])-(B[2]- A[2])*(C[1]- A[1])
	vectorY = -1*((B[0]- A[0])*(C[2]- A[2])-(B[2]- A[2])*(C[0]- A[0]))
	vectorZ = (B[0]- A[0])*(C[1]- A[1])-(B[1]- A[1])*(C[0]- A[0])
	
	result = math.sqrt(math.pow(vectorX, 2) + math.pow(vectorY, 2) + math.pow(vectorZ, 2))
	return result

#-------------------------------------------------------
# Panel 
class VIEW3D_PT_texel_density_checker(Panel):
	bl_label = "Texel Density Checker"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Texel Density"
	#bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(self, context):
		return (context.object is not None)

	def draw(self, context):
		td = context.scene.td
	
		layout = self.layout

		#Split row
		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.5, align=True)
		c = split.column()
		c.label(text="Units:")
		split = split.split()
		c = split.column()
		c.prop(td, 'units', expand=False)
		#----

		layout.label(text="Texture Size:")

		row = layout.row()
		row.prop(td, 'texture_size', expand=False)

		if td.texture_size == '4':
			row = layout.row()
			c = row.column()
			row = c.row()
			split = row.split(factor=0.35, align=True)
			c = split.column()
			c.label(text="Width:")
			split = split.split(factor=0.65, align=True)
			c = split.column()
			c.prop(td, "custom_width")
			split = split.split()
			c = split.column()
			c.label(text="px")

			row = layout.row()
			c = row.column()
			row = c.row()
			split = row.split(factor=0.35, align=True)
			c = split.column()
			c.label(text="Height:")
			split = split.split(factor=0.65, align=True)
			c = split.column()
			c.prop(td, "custom_height")
			split = split.split()
			c = split.column()
			c.label(text="px")
	

		layout.separator()
		row = layout.row()
		row.label(text="Checker Material Method:")
		row = layout.row()
		row.prop(td, 'checker_method', expand=False)
		row = layout.row()
		row.operator("object.checker_assign", text="Assign Checker Material")
		row = layout.row()
		if td.show_restore_mats_btn:
			row.operator("object.checker_restore", text="Restore Materials")
		

		if context.object.mode == 'EDIT':
			layout.separator()
			layout.prop(td, "selected_faces", text="Selected Faces")
		
		layout.separator()
		layout.label(text="Filled UV Space:")
		row = layout.row()
		row.prop(td, "uv_space")
		row.enabled = False
		layout.label(text="Texel Density:")
		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.65, align=True)
		c = split.column()
		c.prop(td, "density")
		split = split.split()
		c = split.column()
		if td.units == '0':
			c.label(text="px/cm")
		if td.units == '1':
			c.label(text="px/m")
		if td.units == '2':
			c.label(text="px/in")
		if td.units == '3':
			c.label(text="px/ft")
		row.enabled = False
		layout.operator("object.texel_density_check", text="Calculate TD")
		layout.operator("object.calculate_to_set", text="Calc -> Set Value")
		layout.separator()
		layout.label(text="Set Texel Density")
		
		#Split row
		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.5, align=True)
		c = split.column()
		c.label(text="Set Method:")
		split = split.split()
		c = split.column()
		c.prop(td, 'set_method', expand=False)
		#----

		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.65, align=True)
		c = split.column()
		c.prop(td, "density_set")
		split = split.split()
		c = split.column()
		if td.units == '0':
			c.label(text="px/cm")
		if td.units == '1':
			c.label(text="px/m")
		if td.units == '2':
			c.label(text="px/in")
		if td.units == '3':
			c.label(text="px/ft")
		layout.operator("object.texel_density_set", text="Set My TD")
		
		#--Aligner Preset Buttons----
		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.33, align=True)
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="20.48").TDValue="20.48"
		if td.units == '1':
			c.operator("object.preset_set", text="2048").TDValue="2048"
		if td.units == '2':
			c.operator("object.preset_set", text="52.0192").TDValue="52.0192"
		if td.units == '3':
			c.operator("object.preset_set", text="624.2304").TDValue="624.2304"
		split = split.split(factor=0.5, align=True)
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="10.24").TDValue="10.24"
		if td.units == '1':
			c.operator("object.preset_set", text="1024").TDValue="1024"
		if td.units == '2':
			c.operator("object.preset_set", text="26.0096").TDValue="26.0096"
		if td.units == '3':
			c.operator("object.preset_set", text="312.1152").TDValue="312.1152"
		split = split.split()
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="5.12").TDValue="5.12"
		if td.units == '1':
			c.operator("object.preset_set", text="512").TDValue="512"
		if td.units == '2':
			c.operator("object.preset_set", text="13.0048").TDValue="13.0048"
		if td.units == '3':
			c.operator("object.preset_set", text="156.0576").TDValue="156.0576"
			
		#--Aligner Preset Buttons----
		row = layout.row()
		c = row.column()
		row = c.row()
		split = row.split(factor=0.33, align=True)
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="2.56").TDValue="2.56"
		if td.units == '1':
			c.operator("object.preset_set", text="256").TDValue="256"
		if td.units == '2':
			c.operator("object.preset_set", text="6.5024").TDValue="6.5024"
		if td.units == '3':
			c.operator("object.preset_set", text="78.0288").TDValue="78.0288"
		split = split.split(factor=0.5, align=True)
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="1.28").TDValue="1.28"
		if td.units == '1':
			c.operator("object.preset_set", text="128").TDValue="128"
		if td.units == '2':
			c.operator("object.preset_set", text="3.2512").TDValue="3.2512"
		if td.units == '3':
			c.operator("object.preset_set", text="39.0144").TDValue="39.0144"
		split = split.split()
		c = split.column()
		if td.units == '0':
			c.operator("object.preset_set", text="0.64").TDValue="0.64"
		if td.units == '1':
			c.operator("object.preset_set", text="64").TDValue="64"
		if td.units == '2':
			c.operator("object.preset_set", text="1.6256").TDValue="1.6256"
		if td.units == '3':
			c.operator("object.preset_set", text="19.5072").TDValue="19.5072"
		
		if context.object.mode == 'OBJECT':
			layout.separator()
			layout.operator("object.texel_density_copy", text="TD from Active to Others")
			
		if context.object.mode == 'EDIT':
			layout.separator()
			layout.operator("object.select_same_texel", text="Select Faces with same TD")
			#Split row
			row = layout.row()
			c = row.column()
			row = c.row()
			split = row.split(factor=0.6, align=True)
			c = split.column()
			c.label(text="Select Threshold:")
			split = split.split()
			c = split.column()
			c.prop(td, "select_td_threshold")
			#----


class TD_Addon_Props(PropertyGroup):
	uv_space: StringProperty(
		name="",
		description="wasting of uv space",
		default="0")
	
	density: StringProperty(
		name="",
		description="Texel Density",
		default="0")
	
	density_set: StringProperty(
		name="",
		description="Texel Density",
		default="0")
	
	tex_size = (('0','512px',''),('1','1024px',''),('2','2048px',''),('3','4096px',''), ('4','Custom',''))
	texture_size: EnumProperty(name="", items = tex_size, update = Change_Texture_Size)
	
	selected_faces: BoolProperty(
		name="Selected Faces",
		description="Operate only on selected faces",
		default = True)
	
	custom_width: StringProperty(
		name="",
		description="Custom Width",
		default="1024",
		update = Change_Texture_Size)
	
	custom_height: StringProperty(
		name="",
		description="Custom Height",
		default="1024",
		update = Change_Texture_Size)
	
	units_list = (('0','px/cm',''),('1','px/m',''), ('2','px/in',''), ('3','px/ft',''))
	units: EnumProperty(name="", items = units_list)
	
	select_td_threshold: StringProperty(
		name="",
		description="Select Threshold",
		default="0.1")
	
	set_method_list = (('0','Each',''),('1','Average',''))
	set_method: EnumProperty(name="", items = set_method_list)

	checker_method_list = (('0','Replace',''), ('1','Store and Replace',''))
	checker_method: EnumProperty(name="", items = checker_method_list)

	show_restore_mats_btn: BoolProperty(
		name="Show Restore Materials Button",
		description="",
		default = False)

	db_path: StringProperty(
		name="DB Path",
		description="Path to DB",
		default="")
#-------------------------------------------------------
classes = (
    VIEW3D_PT_texel_density_checker,
	TD_Addon_Props,
	Texel_Density_Check,
	Texel_Density_Set,
	Texel_Density_Copy,
	Calculated_To_Set,
	Preset_Set,
	Select_Same_TD,
	Checker_Assign,
	Checker_Restore,
)	
def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	
	bpy.types.Scene.td = PointerProperty(type=TD_Addon_Props)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
		
	del bpy.types.Scene.td

if __name__ == "__main__":
	register()