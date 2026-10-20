-- MariaDB anonymous compound block; render via scripts/seed_fixture.py.
-- No identities or credentials default here. Game servers MUST be stopped in
-- the explicitly opted-in disposable isolated instance. SQL cannot attest that.
-- Upstream sql-files/main.sql uses MyISAM: this seed deliberately REFUSES it.
-- Never automatically migrate engines or apply this to a human/shared world.
DELIMITER $$
BEGIN NOT ATOMIC
  DECLARE i INT DEFAULT 0;
  DECLARE aid BIGINT UNSIGNED;
  DECLARE cid BIGINT UNSIGNED;
  DECLARE expected_user VARCHAR(24);
  DECLARE expected_name VARCHAR(24);
  DECLARE actual_user VARCHAR(24);
  DECLARE actual_name VARCHAR(24);
  DECLARE actual_owner BIGINT UNSIGNED;
  DECLARE actual_online INT;
  DECLARE n INT;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  DECLARE EXIT HANDLER FOR NOT FOUND
  BEGIN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'missing exact fixture row';
  END;

  IF COALESCE(@limb_isolated_disposable, 0) <> 1 OR
     COALESCE(@limb_servers_stopped, 0) <> 1 OR
     COALESCE(JSON_VALID(@limb_fixture), 0) <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'explicit isolated offline fixture required';
  END IF;
  IF JSON_TYPE(@limb_fixture) <> 'ARRAY' OR JSON_LENGTH(@limb_fixture) <> 2 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'exactly two fixture pairs required';
  END IF;
  IF JSON_EXTRACT(@limb_fixture, '$[0].account_id') = JSON_EXTRACT(@limb_fixture, '$[1].account_id') OR
     JSON_EXTRACT(@limb_fixture, '$[0].char_id') = JSON_EXTRACT(@limb_fixture, '$[1].char_id') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'fixture IDs must be distinct';
  END IF;

  SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
  START TRANSACTION;
  SELECT COUNT(*) INTO n FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('login', 'char', 'skill')
      AND ENGINE = 'InnoDB';
  IF n <> 3 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed requires all scoped tables InnoDB';
  END IF;

  -- Lock and verify BOTH pairs before the first fixture write.
  WHILE i < 2 DO
    IF COALESCE(JSON_TYPE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].account_id'))), '') <> 'INTEGER' OR
       COALESCE(JSON_TYPE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].char_id'))), '') <> 'INTEGER' OR
       COALESCE(JSON_TYPE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].username'))), '') <> 'STRING' OR
       COALESCE(JSON_TYPE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].character'))), '') <> 'STRING' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invalid fixture pair fields';
    END IF;
    SET aid = JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].account_id'));
    SET cid = JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].char_id'));
    SET expected_user = JSON_UNQUOTE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].username')));
    SET expected_name = JSON_UNQUOTE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].character')));
    IF aid = 0 OR aid >= 4294967296 OR cid = 0 OR cid >= 4294967296 OR
       OCTET_LENGTH(expected_user) NOT BETWEEN 1 AND 23 OR
       OCTET_LENGTH(expected_name) NOT BETWEEN 1 AND 23 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invalid fixture identity';
    END IF;
    SELECT userid INTO actual_user FROM `login` WHERE account_id = aid FOR UPDATE;
    SELECT account_id, name, online INTO actual_owner, actual_name, actual_online
      FROM `char` WHERE char_id = cid FOR UPDATE;
    -- Strong disposable restriction: each fixture account has ONE character.
    -- The indexed account range is locked under SERIALIZABLE, excluding races
    -- with additional characters / online transitions while this seed runs.
    SELECT COUNT(*) INTO n FROM `char` WHERE account_id = aid FOR UPDATE;
    IF BINARY actual_user <> BINARY expected_user OR actual_owner <> aid OR
       BINARY actual_name <> BINARY expected_name OR actual_online <> 0 OR n <> 1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'fixture ownership/offline mismatch';
    END IF;
    SET i = i + 1;
  END WHILE;

  SET i = 0;
  WHILE i < 2 DO
    SET aid = JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].account_id'));
    SET cid = JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].char_id'));
    SET expected_name = JSON_UNQUOTE(JSON_EXTRACT(@limb_fixture, CONCAT('$[', i, '].character')));
    UPDATE `char`
      SET job_level = 10, skill_point = 0, last_map = 'prontera', last_x = 165 - i, last_y = 145
      WHERE char_id = cid AND account_id = aid AND BINARY name = BINARY expected_name AND online = 0;
    INSERT INTO skill (char_id, id, lv, flag) VALUES (cid, 1, 9, 0)
      ON DUPLICATE KEY UPDATE lv = 9, flag = 0;
    SELECT COUNT(*) INTO n FROM `char`
      WHERE char_id = cid AND account_id = aid AND BINARY name = BINARY expected_name AND online = 0
        AND job_level = 10 AND skill_point = 0 AND last_map = 'prontera' AND last_x = 165 - i AND last_y = 145;
    IF n <> 1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed character readback failed';
    END IF;
    SELECT COUNT(*) INTO n FROM skill WHERE char_id = cid AND id = 1 AND lv = 9 AND flag = 0;
    IF n <> 1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed skill readback failed';
    END IF;
    SET i = i + 1;
  END WHILE;
  COMMIT;
  SELECT c.char_id, c.account_id, c.name, c.online, c.job_level, c.skill_point,
         c.last_map, c.last_x, c.last_y, s.id, s.lv, s.flag
    FROM `char` c JOIN skill s ON s.char_id = c.char_id AND s.id = 1
    WHERE c.char_id IN (JSON_EXTRACT(@limb_fixture, '$[0].char_id'), JSON_EXTRACT(@limb_fixture, '$[1].char_id'));
END$$
DELIMITER ;
