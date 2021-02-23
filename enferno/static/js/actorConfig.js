const actorConfig = {
  actorTypes: ["Person", "Entity"],
  actorSex: ["Male", "Female"],
  actorAge: ["Minor", "Adult", "Unknown"],
  actorCivilian: [
    "Unknown",
    "Civilian",
    "Non-Civilian",
    "Police",
    "Other Security Forces"
  ],
  actorEthno: [
    "Alawite",
    "Arab",
    "Armenian",
    "Christian",
    "Circassian",
    "Druze",
    "Ismaili",
    "Kurd",
    "Shiaa",
    "Sunni",
    "Syriac",
    "Turkmen",
    "Unknown"
  ],

  atoaRelateAs: [
    { text: "Same Person", revtext: "Same Person" },
    { text: "Duplicate", revtext: "Duplicate" },
    { text: "Parent", revtext: "Child" },
    { text: "Child", revtext: "Parent" },
    { text: "Sibling", revtext: "Sibling" },
    { text: "Spouse", revtext: "Spouse" },
    { text: "Family member", revtext: "Family member" },
    { text: "Superior officer", revtext: "Subordinate officer" },
    { text: "Subordinate officer", revtext: "Superior officer" },
    { text: "Subunit", revtext: "Subunit" },
    { text: "Alleged Perpetrator", revtext: "Alleged Perpetrator" },
    { text: "Member", revtext: "Member" },
    { text: "Group", revtext: "Group" },
    { text: "Unit", revtext: "Unit" },
    { text: "Other", revtext: "Other" }
  ],

  btoaRelateAs: [
    "Victim",
    "Witness",
    "Perpetrator",
    "Appeared",
    "Participant",
    "Other"
  ],

  itoaRelateAs: [
    "Victim",
    "Witness",
    "Perpetrator",
    "Appeared",
    "Participant",
    "Other"
  ]
};
