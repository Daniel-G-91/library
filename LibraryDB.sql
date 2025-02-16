/* For migrations purposes

create table temp_users ( 
	
	user_name NVARCHAR(50),
	user_email NVARCHAR(50),
	user_password NVARCHAR(200),
);
GO

*/

CREATE TABLE books (

	book_id INT IDENTITY PRIMARY KEY,
	book_title NVARCHAR(50),
	book_author NVARCHAR(50),
	samples INT
);
GO

CREATE TABLE users (

	id INT IDENTITY PRIMARY KEY,
	user_id INT UNIQUE NOT NULL,
	user_name NVARCHAR(50) NOT NULL,
	user_email NVARCHAR(150) NOT NULL,
	user_password NVARCHAR(255) NOT NULL,
	auth_token VARCHAR(64),
	user_status INT DEFAULT 1,
	start_date DATE DEFAULT GETDATE(),
	end_date DATE DEFAULT '9999-12-31'
);
GO

CREATE TABLE transactions (

	id INT IDENTITY PRIMARY KEY,
	user_id INT REFERENCES users(user_id),
	book_id INT REFERENCES books(book_id),
	borrow_date DATE DEFAULT GETDATE(),
	return_date DATE DEFAULT GETDATE()+14,
	trx_status INT DEFAULT 1,
	ext_count INT DEFAULT 0,
	start_date DATE DEFAULT GETDATE(),
	end_date DATE DEFAULT '9999-12-31'
);
GO

--- SEQ ------------------------------------------------------------------------------------------------------------------------------

	CREATE SEQUENCE UserId_Seq
	AS INT
	START WITH 1
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 1000
	NO CYCLE;


-- Create user -----------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE create_user
	@user_name NVARCHAR(50),
	@user_email NVARCHAR(100),
	@user_password NVARCHAR(256)
AS
BEGIN

	SET NOCOUNT ON;

	DECLARE @user_id INT;

	BEGIN TRANSACTION;

	BEGIN TRY

		IF EXISTS (SELECT 1 FROM users WHERE user_email = @user_email AND end_date = '9999-12-31' AND user_status = 1)
		BEGIN
			THROW 50001, 'Email is already registered', 1;
		END

		IF EXISTS (SELECT 1 FROM users WHERE user_name = @user_name AND end_date = '9999-12-31' AND user_status = 1)
		BEGIN
			THROW 50002, 'Username is already registered', 1;
		END

		SET @user_id = NEXT VALUE FOR UserId_Seq;

		INSERT INTO users (user_id, user_name, user_email, user_password) 
		VALUES (@user_id, @user_name, @user_email, @user_password);

		COMMIT TRANSACTION;

	END TRY

	BEGIN CATCH
		ROLLBACK TRANSACTION;
		THROW;
	END CATCH;

END;
GO

-- Borrow ----------------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE borrow_book
    @user_id INT,
    @book_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE 
		@stock INT,
		@books INT;

    BEGIN TRANSACTION;
    BEGIN TRY

        SELECT @stock = samples
        FROM books WITH (UPDLOCK, HOLDLOCK)
        WHERE book_id = @book_id;
        
		SET @books = (SELECT COUNT(*) FROM transactions WHERE user_id = @user_id AND trx_status <> 0 AND end_date = '9999-12-31');

		IF @books >= 3
        BEGIN
            RAISERROR ('You can''t borrow more than 3 books.', 16, 1);
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM transactions WHERE book_id = @book_id AND user_id = @user_id AND trx_status <> 0 AND end_date = '9999-12-31')
        BEGIN
            RAISERROR ('You can''t borrow the same book multiple times.', 16, 1);
            RETURN;
        END

        IF @stock = 0
        BEGIN
            RAISERROR ('This book is not available in stock right now.', 16, 1);
            RETURN;
        END


        INSERT INTO transactions (user_id, book_id)
        VALUES (@user_id, @book_id);

		UPDATE books
		SET samples = samples - 1
		WHERE
			book_id = @book_id;

        COMMIT TRANSACTION;

    END TRY

    BEGIN CATCH
        IF @@TRANCOUNT > 0
        BEGIN
            ROLLBACK TRANSACTION;
        END
		
		DECLARE @ErrorMessage NVARCHAR(4000), @ErrorSeverity INT, @ErrorState INT;
        SELECT @ErrorMessage = ERROR_MESSAGE(), @ErrorSeverity = ERROR_SEVERITY(), @ErrorState = ERROR_STATE();
        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);

    END CATCH
END;
GO

-- Extend ----------------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE extend_borrow
	@user_id INT,
	@book_id INT
AS

BEGIN
	
	BEGIN TRY
		IF EXISTS (SELECT 1 FROM transactions WHERE book_id = @book_id AND user_id = @user_id AND ext_count = 3 AND trx_status = 3 AND end_date = '9999-12-31')
		BEGIN
			THROW 50001, 'You can''t extend more than 3 times.', 1;
		END

		BEGIN
			DECLARE 
				@v_ext_count INT,
				@v_borrow_date DATE,
				@v_return_date DATE;

			SELECT @v_ext_count = ext_count, @v_borrow_date = borrow_date, @v_return_date = return_date
			FROM transactions
			WHERE
				book_id = @book_id
				AND user_id = @user_id
				AND trx_status <> 0
				AND end_date = '9999-12-31';

			INSERT INTO transactions (user_id, book_id, borrow_date, return_date, trx_status, ext_count)
			VALUES (@user_id, @book_id, @v_borrow_date, DATEADD(DAY, 7, @v_return_date), 3, @v_ext_count + 1);
		END

	END TRY

	BEGIN CATCH
		THROW;
	END CATCH

END;
GO
-- Insert in transactions trigg  -----------------------------------------------------------------------------------------------------

CREATE TRIGGER instert_trx_trigg
ON transactions
AFTER INSERT
AS

BEGIN
		DECLARE
			@trx_id INT,
			@user_id INT,
			@book_id INT;

		SELECT @trx_id = id, @user_id = user_id, @book_id = book_id
		FROM inserted
	
		UPDATE transactions
		SET end_date = GETDATE()
		WHERE
			id <> @trx_id
			AND end_date = '9999-12-31'
			AND trx_status <> 0
			AND user_id = @user_id
			AND book_id = @book_id;
	
END;
GO

-- Return ----------------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE return_book
	@user_id INT,
	@book_id INT
AS

BEGIN
	
	SET NOCOUNT ON;

	DECLARE 
		@v_borrow_date DATE,
		@v_ext_count INT;

	BEGIN TRY
		BEGIN TRANSACTION;

		SELECT @v_borrow_date = borrow_date, @v_ext_count = ext_count
		FROM transactions
		WHERE
			trx_status <> 0
			AND user_id = @user_id
			AND book_id = @book_id
			AND end_date = '9999-12-31';

		INSERT INTO transactions (user_id, book_id, borrow_date, return_date, trx_status, ext_count, start_date, end_date)
		VALUES (@user_id, @book_id, @v_borrow_date, GETDATE(), 0, @v_ext_count, GETDATE(), '9999-12-31');

		UPDATE books
		SET samples = samples + 1
		WHERE
			book_id = @book_id;

		COMMIT TRANSACTION;
	END TRY

	BEGIN CATCH
		ROLLBACK TRANSACTION;
		DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
		RAISERROR(@ErrorMessage, 16, 1);
	END CATCH

END;
GO

-- Testing ---------------------------------------------------------------------------------------------------------------------------

SELECT name, type_desc, create_date, modify_date
FROM sys.triggers
ORDER BY name;

SELECT * FROM INFORMATION_SCHEMA.ROUTINES
WHERE ROUTINE_TYPE = 'PROCEDURE';



SELECT * FROM users;
SELECT * FROM transactions;
SELECT * FROM books WHERE book_id = 46

DELETE FROM transactions WHERE end_date = '9999-12-31'

SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'transactions' 

SELECT a.book_id, b.book_title, b.book_author, a.borrow_date, a.return_date
FROM transactions a 
                           LEFT JOIN books b ON a.book_id=b.book_id 
                           WHERE a.trx_status <> 0 AND CAST(a.end_date AS DATE) = CAST('9999-12-31' AS DATE) AND a.user_id = 

EXEC return_book @user_id = 1, @book_id = 64