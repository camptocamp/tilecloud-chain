openlayers_js = """var callback = function(infoLookup) {
    var msg = "";
    if (infoLookup) {
        var info;
        for (var idx in infoLookup) {
            // idx can be used to retrieve layer from map.layers[idx]
            info = infoLookup[idx];
            if (info && info.data) {
                msg += "[" + info.id + "]"
                for (k in info.data) {
                    msg += '<br />' + k + ': ' + info.data[k];
                }
            }
        }
    }
    document.getElementById("attrs").innerHTML = msg;
};

map = new OpenLayers.Map({
    div: "map",
    projection: "{{srs}}",
    controls: [
        new OpenLayers.Control.Navigation(),
        new OpenLayers.Control.Zoom(),
        new OpenLayers.Control.MousePosition(),
        new OpenLayers.Control.LayerSwitcher(),
        new OpenLayers.Control.UTFGrid({
            callback: callback,
            handlerMode: "hover",
            handlerOptions: {
                'delay': 0,
                'pixelTolerance': 0
            },
            reset: function() {}
        })
    ],
    center: [{{center_x}}, {{center_y}}],
    zoom: 0
});

var format = new OpenLayers.Format.WMTSCapabilities();
OpenLayers.Request.GET({
    url: "{{http_url}}/1.0.0/WMTSCapabilities.xml",
    success: function(request) {
        var doc = request.responseXML;
        if (!doc || !doc.documentElement) {
            doc = request.responseText;
        }
        var capabilities = format.read(doc);
        {% for layer in layers %}
        map.addLayer(format.createLayer(capabilities, {
            layer: "{{layer.name}}",
            {% if layer.grid %}
            isBaseLayer: false,
            utfgridResolution: {{layer.resolution}}
            {% else %}
            isBaseLayer: true
            {% endif %}
        }));
        {% endfor %}
    },
    failure: function() {
        alert("Trouble getting capabilities doc");
        OpenLayers.Console.error.apply(OpenLayers.Console, arguments);
    }
});"""
