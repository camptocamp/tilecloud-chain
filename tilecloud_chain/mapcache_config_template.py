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
      <resolutions>{% for r in mapcache['resolutions'] %}{{r}} {% endfor %}</resolutions>
      <origin>top-left</origin>
   </grid>
{% endfor %}
{% for layername, layer in layers.items() %}{% if layer['type'] != 'mapnikh' %}
   <source name="{{layername}}" type="wms">
      <getmap>
         <params>
            <FORMAT>{{layer['mime_type']}}</FORMAT>
            <LAYERS>{{layer['layers']}}</LAYERS>
            <TRANSPARENT>{{'TRUE' if layer['mime_type'] == 'image/png' else 'FALSE'}}</TRANSPARENT>
         </params>
      </getmap>
      <http>
         <url>{{mapserver_url}}</url>
      </http>
   </source>
{% endif %}{% endfor %}
{% for layername, layer in layers.items() %}
   <tileset name="{{layername}}">
      <source>{{layername}}</source>
      <cache>default</cache>
      <grid>{{layer['grid']}}</grid>{% if layer['meta'] %}
      <metatile>{{layer['meta_size']}} {{layer['meta_size']}}</metatile>
      <metabuffer>{{layer['meta_buffer']}}</metabuffer>{% endif %}
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>{%
for dim in layer['dimensions'] %}
        <dimension type="values" name="{{dim['name']}}" default="{{dim['value']}}">{{dim['value']}}</dimension>{%
endfor %}
      </dimensions>
   </tileset>
{% endfor %}

   <service type="wms" enabled="false"/>
   <service type="wmts" enabled="true"/>
   <service type="tms" enabled="false"/>
   <service type="kml" enabled="false"/>
   <service type="gmaps" enabled="false"/>
   <service type="ve" enabled="false"/>
   <service type="demo" enabled="false"/>

   <default_format>JPEG</default_format>
   <errors>report</errors>
   <lock_dir>/tmp</lock_dir>
</mapcache>"""
