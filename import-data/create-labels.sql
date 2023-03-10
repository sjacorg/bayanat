INSERT INTO public.label(
	created_at, updated_at, deleted, id, title, title_ar, comments, comments_ar, "order", verified, for_bulletin, for_actor, for_incident, for_offline, parent_label_id)
  VALUES 
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,1,'Type, Killing of civilians, noncombatants, or POWs','Type, Killing of civilians, noncombatants, or POWs', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,2,'Type, Destruction of civilian property','Type, Destruction of civilian property', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,3,'Type, Destruction of protected property (hospitals, schools, religious buildings)','Type, Destruction of protected property (hospitals, schools, religious buildings)', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,4,'Type, Looting of personal property','Type, Looting of personal property', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,5,'Type, Forced transfer or deportation','Type, Forced transfer or deportation', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,6,'Type, Unlawful detention','Type, Unlawful detention', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,7,'Type, Enslavement','Type, Enslavement', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,8,'Type, Kidnapping or forced disappearance ','Type, Kidnapping or forced disappearance ', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,9,'Type, Torture or indications of torture','Type, Torture or indications of torture', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,10,'Type, Rape or sexual violence','Type, Rape or sexual violence', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,11,'Type, Persecution based on political, racial, ethnic, gender, or sexual orientation','Type, Persecution based on political, racial, ethnic, gender, or sexual orientation', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,12,'Type, Use of weapons that do not discriminate between civilian and military targets (mines, poisons, cluster munitions)','Type, Use of weapons that do not discriminate between civilian and military targets (mines, poisons, cluster munitions)', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,13,'Type, Use of chemical weapons','Type, Use of chemical weapons', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,14,'Type, Use of biological weapons','Type, Use of biological weapons', null, null, null, false, true, false, true, false,null),
    ('2022-06-07 16:51:17.664607', '2022-06-07 16:51:17.664607',null,15,'Type, Other','Type, Other', null, null, null, false, true, false, true, false,null)
  ON CONFLICT (id) 
  DO 
   UPDATE SET title = EXCLUDED.title, title_ar = EXCLUDED.title_ar, verified = EXCLUDED.verified, for_bulletin = EXCLUDED.for_bulletin, for_actor = EXCLUDED.for_actor, for_incident = EXCLUDED.for_incident, for_offline = EXCLUDED.for_offline, parent_label_id = EXCLUDED.parent_label_id;

