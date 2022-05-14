"""
Código modificado partiendo del que se encuentra en https://github.com/imrankhan17/statsbomb-parser
"""

import pandas as pd
import yaml
import os
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

columns = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), 'events.yaml')))

def get_event_name(dictionary: dict):
    '''Gets value from dictionary for key `name` otherwise returns None'''
    try:
        return dictionary.get('name', None)
    except AttributeError:
        return None


def get_events_eventtype(event_type):

    path = os.getcwd()
    path = path + "\\data\\raw_data\\events"
    filelist = os.listdir(path)
    df = pd.DataFrame()
    for file in filelist:
        print(file)
        url = path + "/" + file
        eve = pd.read_json(url, orient='records')
        df_file = pd.DataFrame(eve)

        assert event_type.title() in columns['events'], f'`{event_type}` is not a valid event type'

        # get all events for a given event type
        all_events = [i for _,i in df_file.iterrows() if i['type']['name'] == event_type.title()]
        assert all_events, f'Found 0 events for `{event_type}`'

        # get common attributes
        common_elements = [{key: event.get(key, None) for key in columns['common']} for event in all_events]

        # get attributes specific to this event type
        event_objects = []
        for event in all_events:
            object_dict = {}
            for key in columns[event_type]:
                try:
                    object_dict[key] = event[event_type.replace(' ', '_')].get(key, None)
                except KeyError:
                    object_dict[key] = None
            event_objects.append(object_dict)

        final = [{**i, **j} for i, j in zip(common_elements, event_objects)]

        # combine all into one dataframe and order columns
        df_file = pd.DataFrame(final)
        df_file['event_type'] = event_type
        df_file = df_file[['event_type'] + columns['common'] + columns[event_type]]

        # get names from attributes of form: `{"id" : 7, "name" : "From Goal Kick"}`
        name_cols = [i for i in df_file.columns if i in columns['name_cols']]
        df_file[name_cols] = df_file[name_cols].applymap(get_event_name)

        # split location arrays into their own columns
        try:
            df_file[['start_location_x', 'start_location_y']] = df_file['location'].apply(pd.Series)
        except ValueError:
            pass
        df_file = df_file.drop('location', axis=1)

        # only the shot event type has a z coordinate
        if 'end_location' in df_file.columns:
            try:
                df_file[['end_location_x', 'end_location_y', 'end_location_z']] = df_file['end_location'].apply(pd.Series)
            except ValueError:
                df_file[['end_location_x', 'end_location_y']] = df_file['end_location'].apply(pd.Series)
            df_file = df_file.drop('end_location', axis=1)

        for i, row in df_file.iterrows():
            defenders_between = get_defenders_ff([row["start_location_x"], row["start_location_y"]], row["freeze_frame"])
            df_file.loc[i, "defenders_between"] = defenders_between

        df = pd.concat([df, df_file])

    events_df = df[['period', 'minute', 'second', 'play_pattern', 'team', 'player', 'under_pressure',
                    'body_part', 'type', 'outcome', 'technique', 'first_time', 'follows_dribble', 'redirect',
                    'one_on_one', 'open_goal', 'deflected', 'start_location_x', 'start_location_y',
                    'end_location_x', 'end_location_y', 'end_location_z', 'defenders_between']].copy()


    events_df.replace(to_replace ='"Samuel Eto""o Fils"',value ="Samuel Eto'o Fils") #Reemplazo por posible error futuro
    events_df.to_csv("data/all_shots.csv", index=False)


def get_defenders_ff(location, ff):

    defenders_between=0
    porteria = [[36, 120],[44,120]]
    triangle = Polygon([porteria[0],porteria[1],[location[1],location[0]]])

    freeze_frame = pd.DataFrame(ff)
    for _, player in freeze_frame.iterrows():
        if player['teammate'] == False:
            defender = Point(player['location'][1], player['location'][0])
            if triangle.contains(defender) == True:
                defenders_between+=1

    return defenders_between
