"""SOURCE ONLY native backend; requires an externally admitted bpy module/body.

Does not load files, start Blender, save/export, remove objects, alter weights,
activate a person or establish provenance. In-process observation is not saved
reload, evaluated deformation, sensory validation or complete anatomy.
"""
from __future__ import annotations

import hashlib
import struct


def _point_hash(vertices):
    digest = hashlib.sha256(struct.pack('<Q', len(vertices)))
    for ordinal, vertex in enumerate(vertices):
        digest.update(struct.pack('<Q3f', ordinal, *vertex.co))
    return digest.hexdigest()


def _topology_hash(mesh):
    digest = hashlib.sha256(struct.pack('<3Q', len(mesh.vertices), len(mesh.edges), len(mesh.polygons)))
    for edge in mesh.edges:
        digest.update(struct.pack('<3Q', edge.index, *edge.vertices))
    for polygon in mesh.polygons:
        digest.update(struct.pack('<2Q', polygon.index, len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack('<Q', index))
    return digest.hexdigest()


def _weights_hash(body):
    digest = hashlib.sha256()
    digest.update(struct.pack('<Q', len(body.vertex_groups)))
    for group in body.vertex_groups:
        name = group.name.encode('utf-8')
        digest.update(struct.pack('<2Q', group.index, len(name)))
        digest.update(name)
    digest.update(struct.pack('<Q', len(body.data.vertices)))
    for vertex in body.data.vertices:
        digest.update(struct.pack('<2Q', vertex.index, len(vertex.groups)))
        for group in vertex.groups:
            digest.update(struct.pack('<Qf', group.group, group.weight))
    return digest.hexdigest()


def _matrix_hash(matrix):
    return hashlib.sha256(struct.pack('<16f', *(matrix[row][column] for row in range(4) for column in range(4)))).hexdigest()


class BlenderRestAttachmentBackend:
    """Explicit allocations let the consumer retain handles before configuration.

    `lineage_binding` is separately verified caller evidence, not evidence this
    class discovers. Native mesh/weights/matrix/rig fields below are computed.
    Caller checkpoint/normal-exit/partial-output/resource qualification remains
    necessary before use, including this backend's own retained native handles.
    """
    def __init__(self, bpy, lineage_binding):
        self.bpy = bpy
        self.lineage_binding = lineage_binding
        self.custody = []

    def _retain(self, label, value):
        self.custody.append({'phase': label, 'value': value})
        return value

    def observe(self, body):
        if body.type != 'MESH' or body.mode != 'OBJECT':
            raise ValueError('observer_requires_object_mode_mesh')
        expected_name = self.lineage_binding['candidate_id'] + '__primary_surface'
        if (body.name != expected_name or body.data.name != expected_name
                or body.get('body_class') != 'adult_female'
                or body.get('primary_surface') is not True
                or body.get('generic_identity_neutral_foundation') is not True
                or body.get('private_inactive_authoring_only') is not True
                or body.get('runtime_activation_allowed') is not False
                or body.get('kira_styling_applied') is not False):
            raise ValueError('native_body_is_not_selected_generic_inactive_carrier')
        if body.data.shape_keys is not None or body.animation_data is not None:
            raise ValueError('unexpected_body_shape_keys_or_animation')
        if any(modifier.type != 'ARMATURE' for modifier in body.modifiers):
            raise ValueError('unselected_nonarmature_modifier')
        result = dict(self.lineage_binding)
        result.update({'vertex_count': len(body.data.vertices), 'face_count': len(body.data.polygons),
                       'mesh_points_sha256': _point_hash(body.data.vertices),
                       'mesh_topology_sha256': _topology_hash(body.data), 'weights_sha256': _weights_hash(body),
                       'body_matrix_sha256': _matrix_hash(body.matrix_world),
                       'weight_group_names': sorted(group.name for group in body.vertex_groups),
                       'armature_count': sum(obj.type == 'ARMATURE' for obj in self.bpy.data.objects),
                       'armature_modifier_count': sum(mod.type == 'ARMATURE' for mod in body.modifiers),
                       'parent_name': body.parent.name if body.parent is not None else None})
        modifiers = [mod for mod in body.modifiers if mod.type == 'ARMATURE']
        if len(modifiers) == 1 and modifiers[0].object is not None:
            modifier, armature = modifiers[0], modifiers[0].object
            result.update({'modifier_armature_name': armature.name,
                           'vertex_groups_enabled': modifier.use_vertex_groups,
                           'bone_envelopes_enabled': modifier.use_bone_envelopes,
                           'armature_world_matrix_sha256': _matrix_hash(armature.matrix_world),
                           'parent_inverse_sha256': _matrix_hash(body.matrix_parent_inverse),
                           'attached_bones': {bone.name: {
                               'head': list(bone.head_local), 'tail': list(bone.tail_local),
                               'parent': bone.parent.name if bone.parent is not None else None,
                               'use_deform': bone.use_deform, 'use_connect': bone.use_connect,
                               'matrix_local_sha256': _matrix_hash(bone.matrix_local),
                           } for bone in armature.data.bones}})
        return self._retain('native_observation', result)

    def allocate_armature_data(self, name):
        return self._retain('armature_data', self.bpy.data.armatures.new(name + '__data'))

    def allocate_armature_object(self, name, data):
        return self._retain('armature_object', self.bpy.data.objects.new(name, data))

    def link_armature(self, armature):
        self.bpy.context.collection.objects.link(armature)

    def enter_edit_mode(self, armature):
        if len(armature.data.bones) != 0:
            raise ValueError('new_armature_is_not_empty')
        self.bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        self.bpy.context.view_layer.objects.active = armature
        self.bpy.ops.object.mode_set(mode='EDIT')

    def allocate_bone(self, armature, name):
        return self._retain('edit_bone:' + name, armature.data.edit_bones.new(name))

    def configure_bone(self, bone, operation, parent):
        bone.head = operation['head']
        bone.tail = operation['tail']
        bone.parent = parent
        bone.use_connect = False
        bone.use_deform = operation['use_deform']
        bone.align_roll(operation['roll_normal'])

    def finish_edit_mode(self):
        self.bpy.ops.object.mode_set(mode='OBJECT')

    def allocate_modifier(self, body, name):
        return self._retain('modifier', body.modifiers.new(name=name, type='ARMATURE'))

    def configure_modifier(self, modifier, armature):
        modifier.object = armature
        modifier.use_vertex_groups = True
        modifier.use_bone_envelopes = False

    def copy_body_world(self, body):
        return self._retain('original_body_world', body.matrix_world.copy())

    def armature_world_inverse(self, armature):
        return self._retain('parent_inverse', armature.matrix_world.inverted())

    def bind_parent_preserving_world(self, body, armature, world, inverse):
        body.parent = armature
        body.matrix_parent_inverse = inverse
        body.matrix_world = world
