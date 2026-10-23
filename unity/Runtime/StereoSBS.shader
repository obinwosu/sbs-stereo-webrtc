Shader "Custom/StereoSBS"
{
    Properties
    {
        _MainTex ("SBS Texture", 2D) = "white" {}
        _SwapEyes ("Swap Eyes", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off
        Lighting Off
        ZWrite On

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float _SwapEyes;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float2 uv : TEXCOORD0;
                float4 vertex : SV_POSITION;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                o.vertex = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

                float2 uv = i.uv;
                int eye = unity_StereoEyeIndex; // 0 = left, 1 = right

                if (_SwapEyes > 0.5)
                    eye = 1 - eye;

                if (eye == 0)
                    uv.x = uv.x * 0.5;          // left half
                else
                    uv.x = 0.5 + uv.x * 0.5;    // right half

                return tex2D(_MainTex, uv);
            }
            ENDCG
        }
    }
}