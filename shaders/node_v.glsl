//GLSL
#version 130

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform vec2 screen_size;
uniform vec3 camera_pos;

in vec4 p3d_Vertex;
in uvec4 vertid;

flat out vec2 center;
flat out float point_size;
flat out float id;

void main()
    {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    point_size = max(16.0, screen_size.y/distance(p3d_Vertex.xyz, camera_pos));
    center = (gl_Position.xy / gl_Position.w * 0.5 + 0.5);
    gl_PointSize = point_size;
    id=vertid.x;
    }
