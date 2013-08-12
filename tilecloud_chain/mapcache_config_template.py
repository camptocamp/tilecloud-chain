mapcache_config_template = """<?xml version="1.0" encoding="UTF-8"?>
<mapcache>
    <cache name="default" type="memcache">
       <server>
          <host>{{mapcache['memcache_host']}}</host>
          <port>{{mapcache['memcache_port']}}</port>
       </server>
    </cache>

{% for gridname, grid in grids.items() %}
   <grid name="{{gridname}}">
      <size>{{grid['tile_size']}} {{grid['tile_size']}}</size>
      <extent>{{grid['bbox'][0]}} {{grid['bbox'][1]}} {{grid['bbox'][2]}} {{grid['bbox'][3]}}</extent>
      <srs>{{grid['srs']}}</srs>
      <units>{{grid['unit']}}</units>
      <resolutions>{% for r in grid['resolutions'] %}{{r}} {% endfor %}</resolutions>
      <origin>top-left</origin>
   </grid>
{% endfor %}
{% for layername, layer in layers.items() %}{%
if layer['type'] == 'wms' or 'wms_url' in layer %}
   <source name="{{layername}}" type="wms">
      <getmap>
         <params>{%
         for key, value in layer['params'].items() %}
            <{{key}}>{{value}}</{{key}}>{%
         endfor %}
         </params>
      </getmap>
      <http>
         <url>{{layer['wms_url'] if 'wms_url' in layer else layer['url']}}</url>
         <headers>{%
         for key, value in layer['headers'].items() %}
            <{{key}}>{{value}}</{{key}}>{%
         endfor %}
         </headers>
      </http>
   </source>
{% endif %}{% endfor %}
{% for layername, layer in layers.items() %}{%
if layer['type'] == 'wms' or 'wms_url' in layer %}
   <tileset name="{{layername}}">
      <source>{{layername}}</source>
      <cache>default</cache>
      <grid>{{layer['grid']}}</grid>{% if layer['meta'] %}
      <metatile>{{layer['meta_size']}} {{layer['meta_size']}}</metatile>
      <metabuffer>{{layer['meta_buffer']}}</metabuffer>{% endif %}
      <format>{{layer['mime_type']}}</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>{%
for dim in layer['dimensions'] %}
        <dimension type="values" name="{{dim['name']}}" default="{{dim['default']}}">{{
            ','.join(dim['values'])
        }}</dimension>{%
endfor %}
      </dimensions>
   </tileset>
{% endif %}{% endfor %}

   <format name="image/png" type="PNG">
      <compression>fast</compression>
      <colors>256</colors>
   </format>
   <format name="image/jpeg" type="JPEG">
      <quality>90</quality>
      <photometric>rgb</photometric>
   </format>

   <service type="wms" enabled="false"/>
   <service type="wmts" enabled="true"/>
   <service type="tms" enabled="false"/>
   <service type="kml" enabled="false"/>
   <service type="gmaps" enabled="false"/>
   <service type="ve" enabled="false"/>
   <service type="demo" enabled="false"/>

   <default_format>image/jpeg</default_format>
   <errors>report</errors>
   <lock_dir>/tmp</lock_dir>
</mapcache>"""
