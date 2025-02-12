-- LibraryManagement project

	-- Step 1: Creating database

CREATE TABLE users (

	user_id INT IDENTITY PRIMARY KEY,
	user_name NVARCHAR(50) NOT NULL,
	user_email NVARCHAR(150) NOT NULL,
	user_password NVARCHAR(255) NOT NULL,
	auth_token VARCHAR(64)
);
GO

CREATE TABLE books (

	book_id INT IDENTITY PRIMARY KEY,
	book_title NVARCHAR(50),
	book_author NVARCHAR(50),
	samples INT
);
GO

CREATE TABLE transactions (

	id INT IDENTITY PRIMARY KEY,
	user_id INT REFERENCES users(user_id),
	book_id INT REFERENCES books(book_id),
	borrow_date DATE DEFAULT GETDATE(),
	return_date DATE DEFAULT GETDATE()+14,
	trx_status INT DEFAULT 1,
	ext_count INT DEFAULT 0 
);
GO
	-- Step 2: Logic

	-- Create user -------------------------------------------------------------------------------------------------------------------



ALTER PROCEDURE create_user
	@user_name NVARCHAR(50),
	@user_email NVARCHAR(100),
	@user_password NVARCHAR(128)
AS

BEGIN

	IF EXISTS (SELECT 1 FROM users WHERE user_email = @user_email)
    BEGIN
        RAISERROR('Email is already registered', 16, 1)
        RETURN
    END

	IF EXISTS (SELECT 1 FROM users WHERE user_name = @user_name)
    BEGIN
		RAISERROR('Username is already registered', 16, 1)
        RETURN
    END

	INSERT INTO users (user_name, user_email, user_password) VALUES (@user_name, @user_email, @user_password);
END;
GO

	-- Update Token ---------------------------------------------------------------------------------------------------------------------
	-- not in use --

ALTER PROCEDURE update_token
	@token VARCHAR(64),
	@user_id INT
AS

BEGIN
	UPDATE users
	SET auth_token = @token
	WHERE
		user_id = @user_id;
END;
GO


	-- Borrow ------------------------------------------------------------------------------------------------------------------------

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
        
		SET @books = (SELECT COUNT(*) FROM transactions WHERE user_id = @user_id AND trx_status <> 0);

		IF @books >= 3
        BEGIN
            RAISERROR ('You can''t borrow more than 3 books.', 16, 1);
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM transactions WHERE book_id = @book_id AND user_id = @user_id AND trx_status <> 0)
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
	-- Borrow trigger ----------------------------------------------------------------------------------------------------------------

CREATE TRIGGER borrow_trigg
ON transactions
AFTER INSERT
AS

BEGIN
	
	BEGIN

		UPDATE books
		SET samples = samples - 1
		WHERE
			book_id = (SELECT book_id FROM inserted);

	END;

END;
GO
	-- Extend ------------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE extend_borrow
	@user_id INT,
	@book_id INT
AS

BEGIN
	
	BEGIN TRY
		IF EXISTS (SELECT 1 FROM transactions WHERE book_id = @book_id AND user_id = @user_id AND ext_count = 3 AND trx_status <> 0)
		BEGIN
			THROW 50001, 'You can''t extend more than 3 times.', 1;
		END

		UPDATE transactions
		SET return_date = DATEADD(DAY, 7, return_date), trx_status = 3, ext_count = ext_count+1
		WHERE
			user_id = @user_id
			AND book_id = @book_id
			AND trx_status <> 0;

	END TRY

	BEGIN CATCH
		THROW;
	END CATCH

END;
GO

	-- Return ------------------------------------------------------------------------------------------------------------------------

ALTER PROCEDURE return_book
	@user_id INT,
	@book_id INT
AS

BEGIN

	UPDATE transactions
	SET return_date = GETDATE(), trx_status = 0
	WHERE
		user_id = @user_id
		AND book_id = @book_id
		AND trx_status <> 0;


	UPDATE books
	SET samples = samples + 1
	WHERE
		book_id = @book_id;

END;
GO

-- Testing ------------------------------------------------------------------------------------------------------------------
