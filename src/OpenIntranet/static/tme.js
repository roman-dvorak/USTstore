var element = undefined;


function update_barcode(element, value){
    JsBarcode(element, value, {
        format: "CODE128",
        displayValue: false,
        margin: 0
    });
}

// NASTAVENI MODALU PRO UPRAVU POLOZKY
function OpenArticleEdit(name){
    element = undefined;
    $('#modal-edit-component').modal('show');
    $('#inputCATEGORY_edit').select2({ width: '100%' });

    try {
        $.ajax({
            type: "POST",
            url: "/store/api/product/",
            data: {
                'type':'filter',
                'key':'_id',
                'value': name,
                //'selected': active_categories(),
                //'polarity': $('#category_polarity').is( ":checked" )
            },
            success: function( data, textStatus, jQxhr ){
                element = data[0]
                console.log(element);

                JsBarcode("#edit_barcode",element['_id'], {
                    format: "CODE128",
                    displayValue: false,
                    margin: 0
                });

                if (element == undefined){
                    Lobibox.notify('warning', {
                        title: 'Neznámá položka',
                        msg: 'Položka s tímto ID ještě není zadána ve skladu. Pokračováním vytvoříte novou položku.',
                        delay: 5000,
                        icon: false
                    });
                    product_json = {
                        '_id': id,
                        'name': id,
                        'stock':{},
                        'price':0,
                        'description':'',
                        'category': [],
                    }
                    return 0;
                }

                $('#inputID_edit').val(element['_id']);
                $("#inputID_edit").attr('disabled', true);
                $('#inputNAME_edit').val(element.name || "Bez názvu");
                $('#inputPRICE_edit').val(element.price || 0);
                $('#inputPRICEp_edit').val(element.price_sell || 0);
                $('#inputSELLABLE_edit').prop('checked', element.sellable || false);
                $('#inputDESCRIPTION_edit').val(element.description || "");
                $('#inputCATEGORY_edit').val(element['category']).trigger('change');

                $('#new_param_name')[0].value = ""
                $('#new_param_value')[0].value = ""

                draw_parameters();
                draw_supplier();
                draw_stock();
                draw_tags();

                draw_history(element['_id']);

            },
            error: function( jqXhr, textStatus, errorThrown ){
                console.log( errorThrown );
                Lobibox.notify('error', {
                    msg: 'Načtení položky neproběhlo úspěšně: ' + errorThrown,
                    icon: false,
                });
            }
        });

    }catch(err){
        alert("načítání se nezdařilo. Pro více informací navštivte konzoli... :-( Omlouvám se...");
    }
}


function UpdateFromForm(){
    element['_id'] = $('#inputID_edit')[0].value;
    element.name = $('#inputNAME_edit')[0].value;
    element.description=$('#inputDESCRIPTION_edit')[0].value;
    element.sellable = $('#inputSELLABLE_edit').prop('checked');
    element.price = Number($('#inputPRICE_edit')[0].value);
    element.price_sell = Number($('#inputPRICEp_edit')[0].value);
    element.category = $('#inputCATEGORY_edit').val();

    console.log(element);
}

function WriteToDb(){
    UpdateFromForm();
    $.ajax({
        type: "POST",
        url: "/store/api/update_product/",
        data: {json: JSON.stringify(element)},
        success: function( data, textStatus, jQxhr ){
            console.log(textStatus);
            Lobibox.notify('success', {
                msg: 'Polozka uspesne ulozena: ' + textStatus,
                icon: false,
            });
        },
        error: function( jqXhr, textStatus, errorThrown ){
            console.log( errorThrown );
            Lobibox.notify('error', {
                msg: 'Ukladani nove polozky nebylo uspesne: ' + errorThrown,
                icon: false,
            });
        }
    });
}

function add_parameter(){
  if ((element.parameters || []).length < Number($('#new_param_id')[0].value)){
    if (element.parameters === undefined){
        console.log("Toto jeste neni definovane");
        element.parameters = [];
    }
    var nid = element.parameters.push({
        "name":$('#new_param_name')[0].value,
        "value":$('#new_param_value')[0].value
    });
  }
  else {
    element.parameters[Number($('#new_param_id')[0].value)-1]={
        "name":$('#new_param_name')[0].value,
        "value":$('#new_param_value')[0].value
    };
  }

  $("#new_param_id")[0].value = (element.parameters || []).length+1;
  draw_parameters();
}


function draw_parameters(){
  var parameters = element.parameters;

  if (parameters === undefined || parameters == {} || Array.isArray(parameters) == false){
    parameters = [];
    $("#new_param_id")[0].value = 1;
  }
  $("#param_table_body").empty();
  console.log("All", parameters);

  for (param in parameters){
    var p = parameters[param];

    var html = "<tr><td>" + (Number(param)+1).toString() + "</td><td>" + p.name + "</td><td>"+ p.value +
      "</td><td style='padding: 0pt;'><button class='btn btn-sm'>E</button><button class='btn btn-sm'>X</button><button class='btn btn-sm'>U</button><button class='btn btn-sm'>D</button></td></tr>";
    console.log(html);
    $("#param_table_body").append(html);
  }
  element.parameters = parameters;
}


function add_supplier(){
  var data = {
        "supplier":$('#new_supplier_name')[0].value,
        "sku":$('#new_supplier_sku')[0].value,
        "barcode":$('#new_supplier_code')[0].value,
        "bartype":$('#new_supplier_bartype')[0].value,
        "url":$('#new_supplier_url')[0].value
  };
  if ((element.supplier || []).length < Number($('#new_supplier_id')[0].value)){
      if (element.supplier === undefined){
          console.log("Toto jeste neni definovane");
          element.supplier = [];
      }
      var nid = element.supplier.push(data);
  } else {
      element.supplier[Number($('#new_supplier_id')[0].value)-1] = data;
  }
  $("#new_supplier_id")[0].value = (element.supplier || []).length+1;
  draw_supplier();
}

function draw_supplier(){
  var parameters = element.supplier || [];
  $("#inputSUPPLIER_list").empty();
  console.log("SUPPLIER", parameters);

  for (param in parameters){
    var p = parameters[param];

    var html = "<div class='card'> <small>#"+ (Number(param)+1).toString()+"</small>" + p.supplier +"</div>";
    console.log(html);
    $("#inputSUPPLIER_list").append(html);

  }
}

function draw_stock(){
  var parameters = element.stock || {};
  $("#inputSTOCK_list").empty();
  console.log("STOCK", parameters);

  for (param in parameters){
    var p = parameters[param];
    console.log(p);
    var html = "<div class='card m-0 p-2 mr-2'>"+ param + "<br>" + p.count || Ndef +"</div>";
    console.log(html);
    $("#inputSTOCK_list").append(html);

  }
}

function draw_tags(){
    $('#inputTAG_edit').val(null);
    $("#inputTAG_edit").select2({
        tags: true,
        width: '100%',
        tokenSeparators: [',', ' '],
        data: element.tags,
        insertTag: function (data, tag) {
            // Insert the tag at the end of the results
            console.log(tag);
            data.push(tag);
        }
        });
}


function draw_history(id){
$('#inputHISTORY_edit').empty();
$.ajax({
    type: "POST",
    url: "/store/api/get_history/",
    data: {
        'key':id,
    },
    success: function( data, textStatus, jQxhr ){
        console.log(data);
        for(operation in data){
            var action = data[operation];
            console.log(action);
            var txt = '<div>'+ JSON.stringify(action) +'</div><hr>';
            $("#inputHISTORY_edit").prepend(txt);

        }
    }
});

}



function new_component(){

    $('#modal-edit-component').modal('show');
    $('#inputCATEGORY_edit').select2({ width: '100%' });

    element = {};

    $('#inputID_edit').val("");
    $("#inputID_edit").attr('disabled', false);
    $('#inputNAME_edit').val("Název položky");
    $('#inputPRICE_edit').val(0);
    $('#inputPRICEp_edit').val(0);
    $('#inputSELLABLE_edit').prop('checked', false);
    $('#inputDESCRIPTION_edit').val("");
    $('#inputCATEGORY_edit').val([]).trigger('change');

    $('#new_param_name')[0].value = "";
    $('#new_param_value')[0].value = "";

}