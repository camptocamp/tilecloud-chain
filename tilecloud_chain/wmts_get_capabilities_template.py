wmts_get_capabilities_template = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities version="1.0.0" xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:gml="http://www.opengis.net/gml"
              xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification> </ows:ServiceIdentification>
  <ows:ServiceProvider> </ows:ServiceProvider>
  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="{{getcapabilities}}">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>{%
          if server %}
          <ows:Get xlink:href="{{base_urls[0]}}{{base_url_postfix}}">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>KVP</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>{%
          endif %}
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>{%
          for base_url in base_urls %}
          <ows:Get xlink:href="{{base_url}}{{base_url_postfix}}">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>{%
                if server %}
                <ows:Value>KVP</ows:Value>{%
                endif %}
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>{%
          endfor %}
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>
  <!-- <ServiceMetadataURL xlink:href="" /> -->
  <Contents>
    {% for layername, layer in layers.items() %}
    <Layer>
      <ows:Title>{{layername}}</ows:Title>
      <ows:Identifier>{{layername}}</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>{{layer['wmts_style']}}</ows:Identifier>{%
        for legend in layer['legends'] %}
        <LegendURL format="{{legend['format']}}" xlink:href="{{legend['href']}}" {%
        if 'width' in legend %}width="{{legend['width']}}" {% endif %}{%
        if 'height' in legend %}height="{{legend['height']}}" {% endif %}{%
        if 'max_scale' in legend %}maxScaleDenominator="{{legend['max_scale']}}" {% else %}{%
        if 'max_resolution' in legend %}maxScaleDenominator="{{legend['max_resolution'] / 0.00028}}" {%
        endif %}{% endif %}{%
        if 'min_scale' in legend %}minScaleDenominator="{{legend['min_scale']}}" {% else %}{%
        if 'min_resolution' in legend %}minScaleDenominator="{{legend['min_resolution'] / 0.00028}}" {%
        endif %}{% endif %}/>{%
        endfor %}
      </Style>
      <Format>{{layer['mime_type']}}</Format> {%
      if layer['query_layers'] %}{%
      for info_format in layer['info_formats'] %}
      <InfoFormat>{{infoformat}}</InfoFormat>{%
      endfor %}{%
      endif %}{%
      for dimension in layer['dimensions'] %}
      <Dimension>
        <ows:Identifier>{{dimension['name']}}</ows:Identifier>
        <Default>{{dimension['default']}}</Default> {%
            for value in dimension['values'] %}
        <Value>{{value}}</Value> {%
            endfor %}
      </Dimension>{%
      endfor %}{%
      for base_url in base_urls %}
      <ResourceURL format="{{layer['mime_type']}}" resourceType="tile"
                   template="{{base_url}}{{base_url_postfix}}/1.0.0/{{layername}}/{{layer['wmts_style']}}/{%
                        for dimension in layer['dimensions']
                            %}{{('{' + dimension['name'] + '}')}}{%
                        endfor
                   %}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{{layer['extension']}}" />{%
      endfor %}
      <TileMatrixSetLink>
        <TileMatrixSet>{{layer["grid"]}}</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>
    {% endfor %}

    {% for gridname, grid in grids.items() %}
    <TileMatrixSet>
      <ows:Identifier>{{gridname}}</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:{{
            grid['srs'].replace(':', '::')
      }}</ows:SupportedCRS>{%
        for i, resolution in enumerate(grid['resolutions']) %}{%
        set width = int(ceil(
                (grid['bbox'][2]-grid['bbox'][0]) /
                resolution / grid['tile_size'])) %}{%
        set height = int(ceil(
                (grid['bbox'][3]-grid['bbox'][1]) /
                resolution / grid['tile_size'])) %}{%
        set left = grid['bbox'][0] %}{%
        set top = grid['bbox'][3] %}
      <TileMatrix>
        <ows:Identifier>{{ get_tile_matrix_identifier(grid, resolution=resolution, zoom=i) }}</ows:Identifier>
        <ScaleDenominator>{{resolution / 0.00028}}</ScaleDenominator>
        <TopLeftCorner>{{left}} {{top}}</TopLeftCorner>
        <TileWidth>{{grid['tile_size']}}</TileWidth>
        <TileHeight>{{grid['tile_size']}}</TileHeight>
        <MatrixWidth>{{width}}</MatrixWidth>
        <MatrixHeight>{{height}}</MatrixHeight>
      </TileMatrix>
      {% endfor %}
    </TileMatrixSet>
    {% endfor %}
  </Contents>
</Capabilities>"""
