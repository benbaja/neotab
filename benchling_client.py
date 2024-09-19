from benchling_sdk.helpers.serialization_helpers import fields
from benchling_sdk.models import Field, FieldType, ContainerUpdate, ContainersArchiveReason
import benchling_api_client
import pandas as pd
import sys


def get_display_name(index, loc_df):
    name = loc_df.loc[index]["location_name"]
    display_name = name
    test_slice = loc_df.loc[index]
    parent_id = test_slice["location_parent_id"]
    while parent_id:
        parent_slice = loc_df.loc[parent_id]
        parent_name = parent_slice["location_name"]
        display_name = parent_name + " > " + display_name
        test_slice = parent_slice
        parent_id = test_slice["location_parent_id"]
        
    return display_name

def getContainerDB(benchling_auth, USE_TEST_INSTANCE):
    # different IDs are used for "Generic Location" schemas between test and prod instances
    if USE_TEST_INSTANCE=='True' :
        loc_schema_id = "locsch_2P8oeSYS"
    else :
        loc_schema_id = "locsch_Xz30tLok"
    loc_list = benchling_auth.locations.list(schema_id=loc_schema_id)

    loc_dict = {}
    for loc_list_iter in loc_list:
        for i in loc_list_iter :
            loc_dict[i.id] = {
                'location_name': i.name,
                'location_type': i.fields.additional_properties['Type'].text_value,
                'location_parent_id': i.parent_storage_id
            }

    loc_df = pd.DataFrame.from_dict(loc_dict).T

    if USE_TEST_INSTANCE=='True' :
        # remove conflicting test location, to remove in prod
        loc_df = loc_df.drop(["loc_O1ubOqUx", "loc_BQA7Xgrs", "loc_6CCWn8YH"])

    for i, row in loc_df.iterrows():
        loc_df.loc[i,'location_display_name'] = get_display_name(i, loc_df)

    # same comment as for location schema
    if USE_TEST_INSTANCE=='True' :
        cons_cont_schema_id = "consch_fKIqHlJy"
    else :
        cons_cont_schema_id = "consch_70V9luCB"
    cons_cont_list = benchling_auth.containers.list(schema_id=cons_cont_schema_id, archive_reason="ANY_ARCHIVED_OR_NOT_ARCHIVED")

    cons_cont_dict = {}
    for cont_list_iter in cons_cont_list:
        for i in cont_list_iter:
            if i.archive_record :
                archived = True
            else :
                archived = False
            
            cons_cont_dict[i.barcode] = {
                'name': i.contents[0].entity.name,
                'supplier': i.contents[0].entity.fields.additional_properties["Supplier"].value,
                'ref': i.contents[0].entity.fields.additional_properties["Reference"].value,
                'lot': "", #chem only
                'created': i.created_at,
                'opened': i.fields.additional_properties["Opened"].value,
                'expiry': "", #chem only
                'delivered': "", #chem only
                'grade': "", #chem only
                'msds_fr': "", #chem only
                'msds_en': "", #chem only
                'storage_id': i.parent_storage_id,
                'id': i.id,
                'quantity': i.quantity.value,
                'units': i.quantity.units.value,
                'archived': archived
            }

    # same comment as for location schema
    if USE_TEST_INSTANCE=='True' :
        chem_cont_schema_id = "consch_3uncyyEv"
    else :
        chem_cont_schema_id = "consch_Qn2GFklw"
    chem_cont_list = benchling_auth.containers.list(schema_id=chem_cont_schema_id, archive_reason="ANY_ARCHIVED_OR_NOT_ARCHIVED")

    chem_cont_dict = {}
    for cont_list_iter in chem_cont_list:
        for i in cont_list_iter:
            if i.archive_record :
                archived = True
            else :
                archived = False

            # very annoying but Benchling SDK will return an error if you try to access an UNSET unit :)))
            try :
                units = i.quantity.units.value
            except benchling_api_client.v2.extensions.NotPresentError:
                units = ""

            if len(i.contents) == 1 : 
                chem_cont_dict[i.barcode] = {
                    'name': i.contents[0].entity.name,
                    'supplier': i.contents[0].entity.fields.additional_properties["Supplier"].value,
                    'ref': i.contents[0].entity.fields.additional_properties["Reference"].value,
                    'lot': i.fields.additional_properties["Lot #"].value, 
                    'created': i.created_at,
                    'opened': i.fields.additional_properties["Opened"].value,
                    'expiry': i.fields.additional_properties["Expiry"].value, 
                    'delivered': i.fields.additional_properties["Delivered"].value, 
                    'grade': i.contents[0].entity.fields.additional_properties["Grade"].value, 
                    'msds_fr': i.contents[0].entity.fields.additional_properties["MSDS (French)"].value, 
                    'msds_en': i.contents[0].entity.fields.additional_properties["MSDS (English)"].value, 
                    'storage_id': i.parent_storage_id,
                    'id': i.id,
                    'quantity': i.quantity.value,
                    'units': units,
                    'archived': archived
                }

    # merge consumables and reagents DB
    cont_df = pd.DataFrame.from_dict({**cons_cont_dict, **chem_cont_dict}).T
    # merge container DB to add details about their locations (name)
    cont_df = cont_df.reset_index().merge(
        loc_df.reset_index(names="location_id"), 
        left_on='storage_id', 
        right_on='location_id'
    ).set_index('index')
    cont_df["boxes_count"] = cont_df[cont_df["archived"] == False].groupby(["supplier", "ref"])["id"].transform('nunique')
    cont_df["boxes_count"].fillna(0, inplace=True)
    cont_df["quantity"].fillna(0, inplace=True)
    #cont_df[["boxes_count", "quantity"]].replace(None, 0, inplace=True)
    cont_df = cont_df.astype({"boxes_count":"int", "quantity":"int"})

    return cont_df

def mark_opened_benchling(benchling_auth, id, date):
    update_cont = ContainerUpdate(fields=fields({"Opened": {"value": date, "type": FieldType.DATE}}))
    try :
        benchling_auth.containers.update(container_id=id, container=update_cont)
    except :
        response = False
    else :
        response = True
    finally :
        return response
    
def archive_container(benchling_auth, id) :
    try :
        benchling_auth.containers.archive([id], ContainersArchiveReason.RETIRED, should_remove_barcodes=False)
    except :
        response = False
    else :
        response = True
    finally :
        return response
    
def move_container(benchling_auth, id, loc_barcode) :
    location_id = benchling_auth.locations.bulk_get(barcodes=[loc_barcode])[0].id
    update_cont = ContainerUpdate(parent_storage_id=location_id)
    try :
        benchling_auth.containers.update(container_id=id, container=update_cont)
    except :
        response = False
    else :
        response = True
    finally :
        return response