import bpy
import numpy as np

class SplatCloudProperties(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(type=bpy.types.Image)

class SplatCloudPanel(bpy.types.Panel):
    bl_label = "3DGS Splat Generator"
    bl_idname = "VIEW3D_PT_splat_cloud"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '3DGS'

    def draw(self, context):
        layout = self.layout
        props = context.scene.splat_cloud_props
        layout.prop(props, "image", text="Source Image")
        layout.operator("object.generate_splat_cloud", text="Generate Splat Cloud")

class GenerateSplatCloudOperator(bpy.types.Operator):
    bl_idname = "object.generate_splat_cloud"
    bl_label = "Generate Splat Cloud"

    def execute(self, context):
        props = context.scene.splat_cloud_props
        image = props.image
        if not image:
            self.report({'ERROR'}, "No image selected")
            return {'CANCELLED'}

        width, height = image.size
        pixels = np.array(image.pixels[:]).reshape(-1, 4)
        step_x = max(1, width // 64)
        step_y = max(1, height // 64)

        points, colors, scales = [], [], []
        for y in range(0, height, step_y):
            for x in range(0, width, step_x):
                i = y * width + x
                if i >= len(pixels): continue
                r, g, b, a = pixels[i]
                z = (0.2126 * r + 0.7152 * g + 0.0722 * b) * 0.5
                px = (x / width - 0.5)
                py = (y / height - 0.5)
                pz = z
                points.append((px, py, pz))
                colors.append((r, g, b, 1.0))
                scales.append(0.02)

        mesh = bpy.data.meshes.new("SplatMesh")
        obj = bpy.data.objects.new("SplatObject", mesh)
        bpy.context.collection.objects.link(obj)
        mesh.from_pydata(points, [], [])
        mesh.update()

        mesh.attributes.new(name="Color", type='FLOAT_COLOR', domain='POINT')
        mesh.attributes.new(name="Scale", type='FLOAT', domain='POINT')
        for i, c in enumerate(colors):
            mesh.attributes["Color"].data[i].color = c
            mesh.attributes["Scale"].data[i].value = scales[i]

        gn = bpy.data.node_groups.new("SplatGN", 'GeometryNodeTree')
        modifier = obj.modifiers.new("SplatModifier", type='NODES')
        modifier.node_group = gn

        input_node = gn.nodes.new("NodeGroupInput")
        output_node = gn.nodes.new("NodeGroupOutput")
        input_node.location = (-600, 0)
        output_node.location = (600, 0)

        points_node = gn.nodes.new("GeometryNodeMeshToPoints")
        points_node.location = (-400, 0)
        points_node.inputs["Radius"].default_value = 0.01

        instance_node = gn.nodes.new("GeometryNodeInstanceOnPoints")
        instance_node.location = (0, 0)

        # ✅ 使用 Mesh Circle 作為 splat（向下相容）
        splat_node = gn.nodes.new("GeometryNodeMeshCircle")
        splat_node.location = (-200, -200)
        splat_node.inputs["Vertices"].default_value = 16
        splat_node.inputs["Radius"].default_value = 0.05

        gn.links.new(input_node.outputs[0], points_node.inputs["Mesh"])
        gn.links.new(points_node.outputs["Points"], instance_node.inputs["Points"])
        gn.links.new(splat_node.outputs["Mesh"], instance_node.inputs["Instance"])
        gn.links.new(instance_node.outputs["Instances"], output_node.inputs[0])

        return {'FINISHED'}

classes = [SplatCloudProperties, SplatCloudPanel, GenerateSplatCloudOperator]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.splat_cloud_props = bpy.props.PointerProperty(type=SplatCloudProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.splat_cloud_props

if __name__ == "__main__":
    register()