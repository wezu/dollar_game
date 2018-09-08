//GLSL
#version 140
uniform sampler2D text_tex;
uniform sampler2D value_tex;
uniform sampler2D base_tex;
uniform vec2 screen_size;

flat in vec2 center;
flat in float point_size;
flat in float id;

void main()
    {
    int i=int(id);
    vec3 value=texelFetch(value_tex, ivec2(i, 0), 0).xyz;
    vec2 uv = (gl_FragCoord.xy / screen_size - center) / (point_size / screen_size) + 0.5;
    vec4 color=texture(base_tex, uv);
    //color.rgb*=color.a;
    uv*=0.1; //10x10 tiles in the texture
    uv.x+=value.y;
    uv.y-=value.x+0.1;
    float distance = texture(text_tex, uv).r *value.z +texture(text_tex, uv).g *(1.0-value.z);
    float txt = smoothstep(0.65, 1.0, distance);
    color.rgb*=mix( vec3(0.0, 0.5, 1.0), vec3(1.0, 1.0, 1.0),  clamp(value.z, 0.0, 1.0))-txt*value.z*2.0;


    gl_FragData[0]=color;
    }
